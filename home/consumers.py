import json
import random
import string
import asyncio
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.contrib.auth import get_user_model
from home.models import Challenge
from home.ai_service import check_cpp_code, generate_coding_problem, _groq_request, _gemini_request, _openrouter_request

User = get_user_model()


# Makes a random 6 character room code (letters + numbers).
# If removed, players can't create rooms at all.
# Used in views.py when a new multiplayer room is made.
def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# Turns a player level into a rank name (Beginner, Skilled, etc).
# If removed, ranks show up empty everywhere.
# Called in connect when a player joins a room.
def get_rank(level):
    if level >= 100: return 'God'
    if level >= 75: return 'Legend'
    if level >= 50: return 'Master'
    if level >= 30: return 'Elite'
    if level >= 15: return 'Veteran'
    if level >= 8: return 'Skilled'
    if level >= 3: return 'Intermediate'
    return 'Beginner'


class MultiplayerConsumer(AsyncWebsocketConsumer):

# Runs when a player opens the websocket to a room.
# If removed, nobody can join any multiplayer room.
# WebSocket connects from templates/multiplayer.html.
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code'].upper()
        self.room_group_name = f'multiplayer_{self.room_code}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        room = cache.get(f'room_{self.room_code}')
        if not room:
            await self.close(code=4004)
            return

        if room['status'] == 'finished':
            await self.close(code=4005)
            return

        player = None
        for p in room['players']:
            if p['user_id'] == self.user.id:
                player = p
                break

        if not player:
            if len(room['players']) >= 8:
                await self.close(code=4003)
                return
            avatar_url = f"/api/shop/avatar/?user_id={self.user.id}"
            player = {
                'user_id': self.user.id,
                'username': self.user.username,
                'display_name': self.user.display_name or self.user.username,
                'avatar': avatar_url,
                'level': self.user.level,
                'rank': get_rank(self.user.level),
                'is_ready': False,
                'channel_name': self.channel_name,
                'connected': True,
            }
            room['players'].append(player)
        else:
            player['channel_name'] = self.channel_name
            player['connected'] = True

        room['disconnected_player_id'] = None
        room['forfeit_task'] = None
        cache.set(f'room_{self.room_code}', room, timeout=3600)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_update',
                'players': self._sanitize_players(room['players']),
                'status': room['status'],
            }
        )

# Runs when a player leaves or loses connection.
# If removed, dead players stay in rooms and matches break.
# Handles the 10 second forfeit and room cleanup.
    async def disconnect(self, close_code):
        room = cache.get(f'room_{self.room_code}')
        if room:
            for p in room['players']:
                if p['user_id'] == self.user.id:
                    p['connected'] = False
                    break

            if room['status'] == 'active':
                # For scored games, resolve now if both players already submitted
                scored_games = {'typing': ('typing_results', self._resolve_typing_winner), 'quiz': ('quiz_results', self._resolve_quiz_winner)}
                ct = room.get('challenge_type', '')
                if ct in scored_games:
                    rkey, resolver = scored_games[ct]
                    if rkey in room:
                        if str(self.user.id) in room[rkey] and len(room[rkey]) >= 2:
                            asyncio.create_task(resolver(room))
                            cache.set(f'room_{self.room_code}', room, timeout=3600)
                            return
                        other = None
                        for p in room['players']:
                            if p['user_id'] != self.user.id:
                                other = p
                                break
                        if other and str(other['user_id']) in room[rkey]:
                            asyncio.create_task(resolver(room))
                            cache.set(f'room_{self.room_code}', room, timeout=3600)
                            return

                room['disconnected_player_id'] = self.user.id
                room['disconnect_time'] = time.time()
                cache.set(f'room_{self.room_code}', room, timeout=3600)

# Waits 10s then makes the remaining player the winner.
# If removed, a match just hangs when someone disconnects.
# Scheduled from disconnect().
                async def forfeit_after_delay():
                    await asyncio.sleep(10)
                    current_room = cache.get(f'room_{self.room_code}')
                    if current_room and current_room.get('disconnected_player_id') == self.user.id and current_room['status'] == 'active':
                        # Don't forfeit if the player already submitted a scored result
                        if ct in scored_games:
                            rkey, _ = scored_games[ct]
                            if rkey in current_room and str(self.user.id) in current_room[rkey]:
                                return
                        winner = None
                        for p in current_room['players']:
                            if p['user_id'] != self.user.id:
                                winner = p
                                break
                        if winner:
                            current_room['status'] = 'finished'
                            current_room['winner_id'] = winner['user_id']
                            cache.set(f'room_{self.room_code}', current_room, timeout=3600)
                            for fp in current_room['players']:
                                is_winner = fp['user_id'] == winner['user_id']
                                await self.channel_layer.send(
                                    fp['channel_name'],
                                    {
                                        'type': 'game_over',
                                        'winner_id': winner['user_id'],
                                        'winner_username': winner['display_name'],
                                        'reason': 'opponent_disconnected',
                                        'won': is_winner,
                                        'xp': 0,
                                        'coins': 0,
                                    }
                                )

                asyncio.create_task(forfeit_after_delay())

            elif room['status'] == 'waiting':
                all_disconnected = True
                for p in room['players']:
                    if p['connected']:
                        all_disconnected = False
                        break
                if all_disconnected or len(room['players']) < 2:
                    cache.delete(f'room_{self.room_code}')
                    return

            cache.set(f'room_{self.room_code}', room, timeout=3600)

            sanitized = self._sanitize_players(room['players'])
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_update',
                    'players': sanitized,
                    'status': room['status'],
                }
            )

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

# Routes incoming websocket messages to their handlers.
# If removed, the server ignores everything players send.
# Message types come from templates/multiplayer.html.
    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'ready':
            await self.handle_ready(data)
        elif msg_type == 'progress_update':
            await self.handle_progress_update(data)
        elif msg_type == 'challenge_complete':
            await self.handle_challenge_complete(data)
        elif msg_type == 'answer':
            await self.handle_answer(data)
        elif msg_type == 'start_countdown':
            await self.handle_start_countdown(data)
        elif msg_type == 'update_settings':
            await self.handle_update_settings(data)
        elif msg_type == 'update_challenge_type':
            await self.handle_update_challenge_type(data)
        elif msg_type == 'submit_code':
            await self.handle_coding_submit(data)
        elif msg_type == 'typing_screenshot':
            await self.handle_typing_verify(data)
        elif msg_type == 'reset_room':
            await self.handle_reset_room(data)

# Lets the room creator reset the room back to the lobby.
# If removed, Play Again can never work after a match.
# Triggered by the "reset_room" websocket message.
    async def handle_reset_room(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room:
            return
        is_creator = room['players'] and room['players'][0]['user_id'] == self.user.id
        if not is_creator:
            return
        room['status'] = 'waiting'
        room.pop('challenge', None)
        room.pop('quiz_answers', None)
        room.pop('quiz_record', None)
        for p in room['players']:
            p['is_ready'] = False
        cache.set(f'room_{self.room_code}', room)
        player_data = []
        for pl in room['players']:
            player_data.append({
                'user_id': pl['user_id'],
                'username': pl['username'],
                'display_name': pl.get('display_name', pl['username']),
                'avatar': pl.get('avatar', ''),
                'level': pl.get('level', 1),
                'rank': pl.get('rank', 'Beginner'),
                'is_ready': pl.get('is_ready', False),
                'connected': pl.get('connected', False),
            })
        for p in room['players']:
            if p['connected']:
                await self.channel_layer.send(
                    p['channel_name'],
                    {
                        'type': 'room_reset',
                        'players': player_data,
                        'challenge_type': room['challenge_type'],
                        'custom_settings': room.get('custom_settings'),
                    }
                )
        sanitized = self._sanitize_players(room['players'])
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_update',
                'players': sanitized,
                'status': room['status'],
            }
        )

# Lets the creator switch the game type in the lobby.
# If removed, the lobby game picker does nothing.
# Triggered by "update_challenge_type" from the lobby UI.
    async def handle_update_challenge_type(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room:
            return
        is_creator = room['players'] and room['players'][0]['user_id'] == self.user.id
        if not is_creator:
            return
        new_type = data.get('challenge_type')
        if new_type not in ('typing','quiz','cps','aim3d','reaction','memory','runner','tictactoe','coding'):
            return
        room['challenge_type'] = new_type
        room['custom_settings'] = {}
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        sanitized = self._sanitize_players(room['players'])
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_update',
                'players': sanitized,
                'status': room['status'],
                'challenge_type': new_type,
            }
        )
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'challenge_type_update',
                'challenge_type': new_type,
            }
        )

# Sends the new challenge type to this websocket.
# If removed, players never learn the room switched games.
# Called by the channel layer group broadcast.
    async def challenge_type_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'challenge_type_update',
            'challenge_type': event['challenge_type'],
        }))

# Saves the custom game settings chosen by the creator.
# If removed, custom settings are ignored.
# Triggered by "update_settings" from the lobby UI.
    async def handle_update_settings(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room:
            return
        is_creator = room['players'] and room['players'][0]['user_id'] == self.user.id
        if not is_creator:
            return
        settings = data.get('settings', {})
        room['custom_settings'] = settings
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'settings_update',
                'settings': settings,
            }
        )

# Sends updated custom settings to this websocket.
# If removed, players don't get the new settings.
# Called by the channel layer group broadcast.
    async def settings_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'settings_update',
            'settings': event['settings'],
        }))

# Marks a player ready and starts the countdown when all are ready.
# If removed, games can never start (nobody can be marked ready).
# The message type "ready" is sent from templates/multiplayer.html.
    async def handle_ready(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room:
            return

        is_ready = data.get('ready', True)
        for p in room['players']:
            if p['user_id'] == self.user.id:
                p['is_ready'] = is_ready
                break

        cache.set(f'room_{self.room_code}', room, timeout=3600)

        sanitized = self._sanitize_players(room['players'])
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_update',
                'players': sanitized,
                'status': room['status'],
            }
        )

        all_ready = True
        for p in room['players']:
            if not p['is_ready']:
                all_ready = False
                break
        if all_ready and len(room['players']) >= 2 and room['status'] == 'waiting':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'begin_countdown', 'challenge_type': room['challenge_type']}
            )

# Checks if everyone is ready and kicks off the countdown.
# If removed, the host button to start does nothing.
# Triggered by "start_countdown" from the lobby.
    async def handle_start_countdown(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] != 'waiting':
            return
        all_ready = True
        for p in room['players']:
            if not p['is_ready']:
                all_ready = False
                break
        if all_ready and len(room['players']) >= 2:
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'begin_countdown', 'challenge_type': room['challenge_type']}
            )

# Runs the 3-2-1 countdown then generates and sends the challenge.
# If removed, the game never actually starts.
# Called by the channel layer group broadcast.
    async def begin_countdown(self, event):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] != 'waiting':
            return
        # Only the room creator runs the countdown and generates the challenge.
        # Every player's consumer receives this broadcast; without this gate a
        # non-creator instance can set status='countdown' first, causing the
        # creator's instance to return on the 'waiting' guard above and the
        # room to stall at "Starting game" forever.
        is_creator = room['players'] and room['players'][0]['user_id'] == self.user.id
        if not is_creator:
            return
        room['status'] = 'countdown'
        cache.set(f'room_{self.room_code}', room, timeout=3600)

        for i in range(3, 0, -1):
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'countdown_tick', 'count': i}
            )
            await asyncio.sleep(1)

        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'countdown_tick', 'count': 0}
        )
        await asyncio.sleep(0.3)

        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] != 'countdown':
            return

        challenge_type = event.get('challenge_type', 'typing')
        settings = room.get('custom_settings', {})
        challenge_data = await self._generate_challenge(challenge_type, settings, room)
        # _generate_challenge stores the per-question answer keys on the
        # passed-in room dict. LocMemCache pickles values, so every get
        # returns a fresh copy — the mutation on `room` above does NOT
        # survive unless we carry it over to the fresh room below. Without
        # this, quiz_answers is missing, handle_answer bails, the iframe
        # never gets an answer_result, clicks look dead and the score
        # always comes out 0.
        generated_quiz_answers = room.get('quiz_answers')
        if challenge_data is None:
            # The challenge couldn't be generated (e.g. every AI provider
            # failed for quiz). Abort gracefully — reset the room to the
            # lobby instead of silently swapping in a static fallback.
            room = cache.get(f'room_{self.room_code}')
            if not room:
                return
            room['status'] = 'waiting'
            for p in room['players']:
                p['is_ready'] = False
            cache.set(f'room_{self.room_code}', room, timeout=3600)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'room_error',
                    'message': 'Could not generate this challenge right now. Please try again.',
                }
            )
            return

        room = cache.get(f'room_{self.room_code}')
        if not room:
            return
        room['status'] = 'active'
        room['challenge'] = challenge_data
        if generated_quiz_answers:
            room['quiz_answers'] = generated_quiz_answers
        room['challenge_type'] = challenge_type
        room['started_at'] = time.time()
        cache.set(f'room_{self.room_code}', room, timeout=3600)

        sanitized = self._sanitize_players(room['players'])
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'challenge_start',
                'challenge': challenge_data,
                'challenge_type': challenge_type,
                'players': sanitized,
            }
        )

# Forwards a player's progress to their opponents in real time.
# If removed, opponents can't see each other's progress.
# Triggered by "progress_update" from the game iframe.
    async def handle_progress_update(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] != 'active':
            return

        sender = None
        for p in room['players']:
            if p['user_id'] == self.user.id:
                sender = p
                break

        if sender:
            from_username = sender['display_name']
        else:
            from_username = self.user.username

        for p in room['players']:
            if p['user_id'] != self.user.id and p['connected']:
                await self.channel_layer.send(
                    p['channel_name'],
                    {
                        'type': 'opponent_progress',
                        'progress': data.get('progress', {}),
                        'from_user_id': self.user.id,
                        'from_username': from_username,
                    }
                )

# Routes a finished game to the right winner resolver.
# If removed, finishing a match does nothing.
# Triggered by "challenge_complete" from the game iframe.
    async def handle_challenge_complete(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] == 'finished':
            return

        challenge_type = room.get('challenge_type', '')

        if challenge_type == 'typing':
            await self._handle_typing_complete(room, data)
        elif challenge_type == 'quiz':
            await self._handle_quiz_complete(room, data)
        elif challenge_type == 'cps':
            await self._handle_cps_complete(room, data)
        elif challenge_type == 'aim3d':
            await self._handle_aim3d_complete(room, data)
        elif challenge_type == 'reaction':
            await self._handle_reaction_complete(room, data)
        elif challenge_type == 'memory':
            await self._handle_memory_complete(room, data)
        elif challenge_type == 'runner':
            await self._handle_runner_complete(room, data)
        elif challenge_type == 'tictactoe':
            await self._handle_tictactoe_complete(room, data)
        else:
            await self._handle_instant_complete(room, data)

# Saves a player's result and checks if everyone is done.
# If removed, no game can be resolved.
# Called by the _handle_*_complete methods.
    async def _store_result_and_check(self, room, data, result_key, resolver_method):
        if result_key not in room:
            room[result_key] = {}

        result = data.get('result', {})
        my_id = str(self.user.id)
        entry = {'user_id': self.user.id, 'username': self.user.display_name or self.user.username}
        entry.update(result)
        entry['completion_time'] = data.get('completion_time')
        room[result_key][my_id] = entry
        cache.set(f'room_{self.room_code}', room, timeout=3600)

        connected = []
        for p in room['players']:
            if p['connected']:
                connected.append(p)

        all_done = True
        for p in connected:
            if str(p['user_id']) not in room[result_key]:
                all_done = False
                break

        if not all_done:
            asyncio.create_task(self._scored_timeout_wait(self.room_code, result_key, resolver_method))
            return False
        return True

# Waits 60s then forces a result if the opponent never finishes.
# If removed, a match can hang forever waiting.
# Scheduled from _store_result_and_check.
    async def _scored_timeout_wait(self, room_code, result_key, resolver_method):
        await asyncio.sleep(60)
        room = cache.get(f'room_{room_code}')
        if not room or room['status'] == 'finished':
            return
        if result_key not in room or len(room[result_key]) == 0:
            return
        await resolver_method(room)

# Stores typing results and resolves the winner.
# If removed, typing matches never end.
# Called when a typing challenge is completed.
    async def _handle_typing_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'typing_results', self._resolve_typing_winner)
        if ready:
            await self._resolve_typing_winner(room)

# Stores quiz results and resolves the winner.
# If removed, quiz matches never end.
# Called when a quiz challenge is completed.
    async def _handle_quiz_complete(self, room, data):
        # The server tracks every answer in quiz_record, so the score is
        # authoritative. Falls back to the client score if no answers were
        # validated (legacy clients).
        quiz_record = room.get('quiz_record', {}).get(str(self.user.id))
        if quiz_record:
            data['result']['score'] = int(sum(1 for v in quiz_record.values() if v))
        ready = await self._store_result_and_check(room, data, 'quiz_results', self._resolve_quiz_winner)
        if ready:
            await self._resolve_quiz_winner(room)

# Validates a single quiz answer and replies privately with the result.
# If removed, multiplayer quiz answers are never checked.
# Triggered by "answer" from the quiz iframe.
    async def handle_answer(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] != 'active':
            return
        quiz_answers = room.get('quiz_answers')
        if not quiz_answers:
            return
        index = str(data.get('index'))
        chosen = data.get('answer')
        entry = quiz_answers.get(index)
        if not entry:
            return
        correct = entry.get('answer') == chosen
        quiz_record = room.setdefault('quiz_record', {})
        per_user = quiz_record.setdefault(str(self.user.id), {})
        per_user[index] = bool(correct)
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self.channel_layer.send(
            self.channel_name,
            {
                'type': 'answer_result',
                'index': int(index),
                'correct': correct,
                'correct_answer': entry.get('answer'),
                'correct_answer_en': entry.get('answer_en', ''),
                'explanation': entry.get('explanation', ''),
            }
        )

# Sends a per-question answer result to this websocket.
# If removed, the quiz iframe never learns if an answer was right.
# Called by the channel layer direct send.
    async def answer_result(self, event):
        await self.send(text_data=json.dumps({
            'type': 'answer_result',
            'index': event.get('index'),
            'correct': event.get('correct'),
            'correct_answer': event.get('correct_answer'),
            'correct_answer_en': event.get('correct_answer_en', ''),
            'explanation': event.get('explanation', ''),
        }))

# Stores CPS results and resolves the winner.
# If removed, CPS matches never end.
# Called when a CPS challenge is completed.
    async def _handle_cps_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'cps_results', self._resolve_cps_winner)
        if ready:
            await self._resolve_cps_winner(room)

# Picks the winner of a CPS match (highest CPS, lowest time).
# If removed, CPS matches never end.
# Called from _handle_cps_complete and the timeout.
    async def _resolve_cps_winner(self, room):
        if 'cps_results' not in room or not room['cps_results']:
            return
            
        results = list(room['cps_results'].values())
        
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            # Try a few field names for the CPS value
            cps_val = r.get('cps') or r.get('score') or r.get('current_score') or 0
            try:
                r['cps_float'] = float(cps_val)
            except (ValueError, TypeError):
                r['cps_float'] = 0
            if 'completion_time' in r:
                try:
                    r['time_float'] = float(r['completion_time'])
                except (ValueError, TypeError):
                    r['time_float'] = 999999
            else:
                r['time_float'] = 999999
        
# Sort key for CPS results (highest CPS first).
# If removed, the sort in _resolve_cps_winner breaks.
# Only used in _resolve_cps_winner.
        def cps_sort_key(r):
            return (-r.get('cps_float', 0), r.get('time_float', 999999))

        results.sort(key=cps_sort_key)
        
        if not results:
            return
            
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

# Picks the typing winner by wpm, then accuracy, then time.
# If removed, typing matches never end.
# Called from _handle_typing_complete.
    async def _resolve_typing_winner(self, room):
        results = list(room['typing_results'].values())
# Sort key for typing results.
# If removed, the sort in _resolve_typing_winner breaks.
# Only used in _resolve_typing_winner.
        def typing_sort_key(r):
            return (-float(r.get('wpm', 0)), -float(r.get('accuracy', 0)), float(r.get('time', 0)))

        results.sort(key=typing_sort_key)
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner['username']
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

# Picks the quiz winner by score, then time.
# If removed, quiz matches never end.
# Called from _handle_quiz_complete.
    async def _resolve_quiz_winner(self, room):
        results = list(room['quiz_results'].values())
# Sort key for quiz results.
# If removed, the sort in _resolve_quiz_winner breaks.
# Only used in _resolve_quiz_winner.
        def quiz_sort_key(r):
            return (-int(r.get('score', 0)), float(r.get('completion_time') or 999999), int(r.get('total', 1)))

        results.sort(key=quiz_sort_key)
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner['username']
        # Tie handling: any player with the SAME top score also wins (e.g.
        # both answered nothing → both 0). Only break the tie on score, not
        # on time — an unanswered quiz shouldn't crown a random winner.
        top_score = int(winner.get('score', 0))
        winner_ids = [winner_id]
        for r in results[1:]:
            if int(r.get('score', 0)) == top_score:
                winner_ids.append(r['user_id'])
            else:
                break
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id, winner_ids)

# Stores aim3d results and resolves the winner.
# If removed, aim3d matches never end.
# Called when an aim3d challenge is completed.
    async def _handle_aim3d_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'aim3d_results', self._resolve_aim3d_winner)
        if ready:
            await self._resolve_aim3d_winner(room)

# Stores reaction results and resolves the winner.
# If removed, reaction matches never end.
# Called when a reaction challenge is completed.
    async def _handle_reaction_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'reaction_results', self._resolve_reaction_winner)
        if ready:
            await self._resolve_reaction_winner(room)

# Stores memory results and resolves the winner.
# If removed, memory matches never end.
# Called when a memory challenge is completed.
    async def _handle_memory_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'memory_results', self._resolve_memory_winner)
        if ready:
            await self._resolve_memory_winner(room)

# Stores runner results and resolves the winner.
# If removed, runner matches never end.
# Called when a runner challenge is completed.
    async def _handle_runner_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'runner_results', self._resolve_runner_winner)
        if ready:
            await self._resolve_runner_winner(room)

# Stores tictactoe results and resolves the winner.
# If removed, tictactoe matches never end.
# Called when a tictactoe challenge is completed.
    async def _handle_tictactoe_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'tictactoe_results', self._resolve_tictactoe_winner)
        if ready:
            await self._resolve_tictactoe_winner(room)

# Picks the aim3d winner (highest score, lowest time).
# If removed, aim3d matches never end.
# Called from _handle_aim3d_complete.
    async def _resolve_aim3d_winner(self, room):
        if 'aim3d_results' not in room or not room['aim3d_results']:
            return
        results = list(room['aim3d_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['score_float'] = float(r.get('current_score') or r.get('score', 0))
            r['time_float'] = float(r.get('completion_time') or 999999)

# Sort key for aim3d results.
# If removed, the sort in _resolve_aim3d_winner breaks.
# Only used in _resolve_aim3d_winner.
        def aim3d_sort_key(r):
            return (-r.get('score_float', 0), r.get('time_float', 999999))

        results.sort(key=aim3d_sort_key)
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

# Picks the reaction winner (lowest avg time).
# If removed, reaction matches never end.
# Called from _handle_reaction_complete.
    async def _resolve_reaction_winner(self, room):
        if 'reaction_results' not in room or not room['reaction_results']:
            return
        results = list(room['reaction_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['avg_float'] = float(r.get('avg_time') or r.get('avg', 9999))
            r['time_float'] = float(r.get('completion_time') or 999999)

# Sort key for reaction results.
# If removed, the sort in _resolve_reaction_winner breaks.
# Only used in _resolve_reaction_winner.
        def reaction_sort_key(r):
            return (r.get('avg_float', 9999), r.get('time_float', 999999))

        results.sort(key=reaction_sort_key)
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

# Picks the memory winner (highest level, lowest time).
# If removed, memory matches never end.
# Called from _handle_memory_complete.
    async def _resolve_memory_winner(self, room):
        if 'memory_results' not in room or not room['memory_results']:
            return
        results = list(room['memory_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['level_int'] = int(r.get('level', r.get('current_level', 0)) or 0)
            r['time_float'] = float(r.get('completion_time') or 999999)

# Sort key for memory results.
# If removed, the sort in _resolve_memory_winner breaks.
# Only used in _resolve_memory_winner.
        def memory_sort_key(r):
            return (-r.get('level_int', 0), r.get('time_float', 999999))

        results.sort(key=memory_sort_key)
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

# Picks the runner winner (highest score, lowest time).
# If removed, runner matches never end.
# Called from _handle_runner_complete.
    async def _resolve_runner_winner(self, room):
        if 'runner_results' not in room or not room['runner_results']:
            return
        results = list(room['runner_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['score_float'] = float(r.get('score', r.get('current_score', 0)) or 0)
            r['time_float'] = float(r.get('completion_time') or 999999)

# Sort key for runner results.
# If removed, the sort in _resolve_runner_winner breaks.
# Only used in _resolve_runner_winner.
        def runner_sort_key(r):
            return (-r.get('score_float', 0), r.get('time_float', 999999))

        results.sort(key=runner_sort_key)
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

# Picks the tictactoe winner (most wins, lowest time).
# If removed, tictactoe matches never end.
# Called from _handle_tictactoe_complete.
    async def _resolve_tictactoe_winner(self, room):
        if 'tictactoe_results' not in room or not room['tictactoe_results']:
            return
        results = list(room['tictactoe_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['wins_int'] = int(r.get('wins', 0) or 0)
            r['time_float'] = float(r.get('completion_time') or 999999)

# Sort key for tictactoe results.
# If removed, the sort in _resolve_tictactoe_winner breaks.
# Only used in _resolve_tictactoe_winner.
        def tictactoe_sort_key(r):
            return (-r.get('wins_int', 0), r.get('time_float', 999999))

        results.sort(key=tictactoe_sort_key)
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

# Handles games that end instantly (first one done wins).
# If removed, those games never end.
# Called from handle_challenge_complete.
    async def _handle_instant_complete(self, room, data):
        winner_key = f'room_winner_{self.room_code}'
        winner_claim = {
            'user_id': self.user.id,
            'username': self.user.display_name or self.user.username,
        }

        if cache.add(winner_key, json.dumps(winner_claim), timeout=3600):
            room['status'] = 'finished'
            room['winner_id'] = self.user.id
            room['winner_username'] = self.user.display_name or self.user.username
            cache.set(f'room_{self.room_code}', room, timeout=3600)
            winner_id = room['winner_id']
        else:
            winner_data = json.loads(cache.get(winner_key) or '{}')
            winner_id = winner_data.get('user_id')

        await self._send_game_over(room, winner_id)

# Updates a player's stats after a match (plays, wins, best score).
# If removed, stats never update on the profile.
# Runs in a thread from _send_game_over.
    def _update_game_stats(self, user_id, game, result_data, won):
        from .models import UserGameStats
        from django.utils import timezone
        try:
            stats, _ = UserGameStats.objects.get_or_create(user_id=user_id, game=game)
            stats.plays += 1
            if won:
                stats.wins += 1
            else:
                stats.losses += 1
            # Pull primary/secondary score based on game type
            score_map = {
                'typing': (result_data.get('wpm', 0), result_data.get('accuracy', 0)),
                'quiz': (result_data.get('score', 0), result_data.get('total', 0)),
                'cps': (result_data.get('cps', 0), result_data.get('clicks', 0)),
                'reaction': (result_data.get('avg_time', 0) or result_data.get('best_time', 0), result_data.get('attempts', 0)),
                'memory': (result_data.get('current_level', 0) or result_data.get('level', 0), result_data.get('moves', 0)),
                'aim3d': (result_data.get('current_score', 0) or result_data.get('score', 0), result_data.get('accuracy', 0)),
                'runner': (result_data.get('current_score', 0) or result_data.get('score', 0), result_data.get('deaths', 0)),
                'tictactoe': (result_data.get('wins', 0) or result_data.get('score', 0), result_data.get('moves', 0)),
            }
            score, score_secondary = score_map.get(game, (0, 0))
            if score > stats.best_score:
                stats.best_score = int(score)
            if score_secondary > stats.best_score_secondary:
                stats.best_score_secondary = int(score_secondary)
            # Track runner deaths
            if game == 'runner':
                stats.deaths += int(result_data.get('deaths', 0))
            stats.last_played = timezone.now()
            stats.save()
        except Exception:
            pass

# Sends the game_over message with rewards to every player.
# If removed, nobody gets XP/coins or sees results.
# Called by all the _resolve_*_winner methods.
    async def _send_game_over(self, room, winner_id, winner_ids=None):
        fresh = cache.get(f'room_{self.room_code}')
        if fresh:
            room = fresh
        players = room['players']
        # Support ties: winner_ids is a list of all winners (equal top score).
        # Callers that don't pass it keep the old single-winner behaviour.
        if not winner_ids:
            winner_ids = [winner_id]
        winner_set = set(winner_ids)
        xp_base = 50
        coin_base = 10
        xp_winner = int(xp_base * 1.5)
        coins_winner = coin_base + 50
        xp_loser = int(xp_base * 0.5)
        coins_loser = 0

        for p in players:
            if p['user_id'] in winner_set:
                await self._award_xp_coins(p['user_id'], xp_winner, coins_winner)
            else:
                await self._award_xp_coins(p['user_id'], xp_loser, coins_loser)

        ctype = room.get('challenge_type', '')
        result_key_map = {
            'typing': 'typing_results',
            'quiz': 'quiz_results',
            'cps': 'cps_results',
            'reaction': 'reaction_results',
            'memory': 'memory_results',
            'aim3d': 'aim3d_results',
            'runner': 'runner_results',
            'tictactoe': 'tictactoe_results',
        }
        result_key = result_key_map.get(ctype)
        results = {}
        if result_key:
            results = room.get(result_key, {})

        if ctype:
            for p in players:
                player_result = results.get(str(p['user_id']), {})
                await asyncio.to_thread(
                    self._update_game_stats,
                    p['user_id'],
                    ctype,
                    player_result,
                    p['user_id'] in winner_set,
                )

        for p in room['players']:
            is_winner = p['user_id'] in winner_set
            if is_winner:
                xp_to_send = xp_winner
                coins_to_send = coins_winner
            else:
                xp_to_send = xp_loser
                coins_to_send = coins_loser
            p_id_str = str(p['user_id'])
            self_result_data = results.get(p_id_str, {})
            opponent_result_data = {}
            for r_id, r_data in results.items():
                if r_id != p_id_str:
                    opponent_result_data = r_data
                    break

            await self.channel_layer.send(
                p['channel_name'],
                {
                    'type': 'game_over',
                    'winner_id': winner_id,
                    'winner_username': room.get('winner_username', ''),
                    'challenge_type': ctype,
                    'reason': 'completed',
                    'won': is_winner,
                    'is_tie': len(winner_set) > 1,
                    'winner_ids': list(winner_set),
                    'xp': xp_to_send,
                    'coins': coins_to_send,
                    'xp_winner': xp_winner,
                    'coins_winner': coins_winner,
                    'xp_loser': xp_loser,
                    'coins_loser': coins_loser,
                    'self_result': self_result_data,
                    'opponent_result': opponent_result_data,
                    'all_results': results,
                }
            )

# Checks submitted C++ code and declares the winner if it passes.
# If removed, the coding challenge can't be won.
# Triggered by "submit_code" from the coding game.
    async def handle_coding_submit(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] == 'finished':
            return
        if room.get('winner_id') is not None:
            await self.send(text_data=json.dumps({
                'type': 'code_result',
                'passed': False,
                'feedback': 'Someone already won!',
            }))
            return

        code = data.get('code', '')
        problem = data.get('problem', '')

        result = await asyncio.to_thread(check_cpp_code, code, problem)
        passed = result.get('passed', False)
        feedback = result.get('feedback', 'Code evaluated.')

        if passed:
            room['status'] = 'finished'
            room['winner_id'] = self.user.id
            room['winner_username'] = self.user.display_name or self.user.username
            cache.set(f'room_{self.room_code}', room, timeout=3600)

            winner_id = room['winner_id']
            players = room['players']
            xp_base = 50
            coin_base = 10
            xp_winner = int(xp_base * 1.5)
            coins_winner = coin_base + 50
            xp_loser = int(xp_base * 0.5)
            coins_loser = 0

            for p in players:
                if p['user_id'] == winner_id:
                    await self._award_xp_coins(p['user_id'], xp_winner, coins_winner)
                else:
                    await self._award_xp_coins(p['user_id'], xp_loser, coins_loser)

            coding_results = {}
            for p in room['players']:
                coding_results[str(p['user_id'])] = {
                    'solved': p['user_id'] == winner_id,
                }
            for p in room['players']:
                is_winner = p['user_id'] == winner_id
                if is_winner:
                    xp_to_send = xp_winner
                    coins_to_send = coins_winner
                else:
                    xp_to_send = xp_loser
                    coins_to_send = coins_loser
                self_result = coding_results.get(str(p['user_id']), {})
                opponent_result = {}
                for op in room['players']:
                    if op['user_id'] != p['user_id']:
                        opponent_result = coding_results.get(str(op['user_id']), {})
                        break
                await self.channel_layer.send(
                    p['channel_name'],
                    {
                        'type': 'game_over',
                        'winner_id': winner_id,
                        'winner_username': room.get('winner_username', ''),
                        'reason': 'completed',
                        'won': is_winner,
                        'xp': xp_to_send,
                        'coins': coins_to_send,
                        'xp_winner': xp_winner,
                        'coins_winner': coins_winner,
                        'xp_loser': xp_loser,
                        'coins_loser': coins_loser,
                        'self_result': self_result,
                        'opponent_result': opponent_result,
                        'all_results': coding_results,
                    }
                )

            await self.send(text_data=json.dumps({
                'type': 'code_result',
                'passed': True,
                'feedback': feedback or 'Correct! You won!',
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'code_result',
                'passed': False,
                'feedback': feedback or 'Your code has errors. Try again!',
            }))

# Stores typing screenshots for verification.
# If removed, screenshot checks never work.
# Triggered by "typing_screenshot" from the typing game.
    async def handle_typing_verify(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] == 'finished':
            return
        if not room.get('typing_screenshots'):
            room['typing_screenshots'] = {}
        user_id = str(self.user.id)
        screenshot = data.get('screenshot', '')
        if not screenshot:
            await self.send(text_data=json.dumps({
                'type': 'typing_verify_result',
                'status': 'error',
                'message': 'No screenshot received',
            }))
            return
        room['typing_screenshots'][user_id] = {
            'screenshot': screenshot,
            'username': self.user.display_name or self.user.username,
        }
        cache.set(f'room_{self.room_code}', room, timeout=3600)

        players_in_room = len(room['players'])
        submitted = len(room['typing_screenshots'])

        if players_in_room < 2:
            await self.send(text_data=json.dumps({
                'type': 'typing_verify_result',
                'status': 'error',
                'message': 'Typing screenshot comparison requires at least 2 players',
            }))
            return

        if submitted >= players_in_room:
            await self.send(text_data=json.dumps({
                'type': 'typing_verify_result',
                'status': 'verified',
                'message': 'Screenshots received',
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'typing_verify_result',
                'status': 'waiting',
                'message': f'Waiting for opponent... ({submitted}/{players_in_room})',
            }))

# Builds the challenge object for a game type (passage, quiz, etc).
# If removed, no challenge can ever start.
# Called from begin_countdown.
    async def _generate_challenge(self, challenge_type, settings=None, room=None):
        settings = settings or {}
        if challenge_type == 'typing':
            passages = [
                "the sun was setting behind the mountains casting long shadows across the valley a cool breeze carried the scent of pine and wildflowers through the air birds chirped their evening songs as they settled into their nests for the night",
                "in the heart of the digital age technology continues to reshape our world at an unprecedented pace from artificial intelligence to quantum computing innovations are opening doors that were once thought impossible the future belongs to those who can adapt and learn",
                "she walked through the ancient forest where towering oaks stood like silent guardians sunlight filtered through the dense canopy creating patterns of light and shadow on the mossy ground a deer appeared silently between the trees its eyes curious yet cautious",
                "the city streets were alive with energy as people hurried past colorful market stalls the aroma of freshly baked bread mixed with the scent of rain on warm pavement street musicians played cheerful melodies while children laughed and danced in the square",
                "deep beneath the ocean waves lay a hidden world of wonder coral reefs painted in vibrant colors stretched as far as the eye could see schools of shimmering fish darted through ancient underwater caves their scales catching rays of filtered sunlight",
            ]
            duration = settings.get('duration', 30)
            passage = random.choice(passages)
            return {
                'type': 'typing',
                'passage': passage,
                'word_count': len(passage.split()),
                'target_wpm': settings.get('target_wpm', 35),
                'duration': duration,
            }

        elif challenge_type == 'quiz':
            topic = settings.get('topic', 'mixed')
            question_count = int(settings.get('question_count', 5) or 5)
            if question_count > 10:
                question_count = 10
            questions = await self._generate_quiz_questions(topic, question_count)
            if not questions:
                return None
            sanitized = []
            quiz_answers = {}
            for idx, q in enumerate(questions):
                opts = q.get('options') or q.get('opts') or []
                sanitized.append({
                    'q': q.get('question') or q.get('q'),
                    'opts': opts,
                    'qid': idx,
                })
                quiz_answers[str(idx)] = {
                    'answer': q.get('answer'),
                    'answer_en': q.get('answer_en', ''),
                    'explanation': q.get('explanation', ''),
                }
            if room is not None:
                room['quiz_answers'] = quiz_answers
            return {
                'type': 'quiz',
                'topic': topic,
                'questions': sanitized,
                'question_count': len(sanitized),
            }

        elif challenge_type == 'cps':
            time_limit = settings.get('time_limit', 10)
            target_cps = settings.get('target_cps', random.choice([8, 10, 12, 15]))
            return {
                'type': 'cps',
                'target_cps': target_cps,
                'time_limit': time_limit,
                'target_score': target_cps * time_limit,
            }

        elif challenge_type == 'aim3d':
            target_score = settings.get('target_score', random.choice([500, 1000, 1500, 2000]))
            time_limit = settings.get('time_limit', 30)
            target_size = settings.get('target_size', 'medium')
            target_speed = settings.get('target_speed', 'normal')
            size_map = {'small': 25, 'medium': 35, 'large': 50}
            speed_map = {'slow': 2.5, 'normal': 4, 'fast': 6}
            return {
                'type': 'aim3d',
                'target_score': target_score,
                'time_limit': time_limit,
                'target_size': target_size,
                'target_size_px': size_map.get(target_size, 35),
                'target_speed': speed_map.get(target_speed, 4),
                'description': f'Score {target_score} points in {time_limit}s',
            }

        elif challenge_type == 'reaction':
            target_avg = settings.get('target_avg', random.choice([250, 200, 180, 150]))
            attempts = settings.get('attempts', 5)
            return {
                'type': 'reaction',
                'target_avg': target_avg,
                'attempts': attempts,
                'description': f'Avg reaction ≤ {target_avg}ms',
            }

        elif challenge_type == 'memory':
            target_level = settings.get('target_level', random.choice([5, 6, 7, 8]))
            grid_size = settings.get('grid_size', 4)
            return {
                'type': 'memory',
                'target_level': target_level,
                'grid_size': grid_size,
                'description': f'Reach level {target_level}',
            }

        elif challenge_type == 'runner':
            target_score = settings.get('target_score', random.choice([5000, 10000, 15000, 20000]))
            time_limit = settings.get('time_limit', 120)
            lives = settings.get('lives', 3)
            return {
                'type': 'runner',
                'target_score': target_score,
                'time_limit': time_limit,
                'lives': lives,
                'difficulty': settings.get('difficulty', 'normal'),
                'description': f'Score {target_score} points',
            }

        elif challenge_type == 'tictactoe':
            target_wins = settings.get('target_wins', random.choice([1, 2, 3]))
            grid_size = settings.get('grid_size', 3)
            return {
                'type': 'tictactoe',
                'target_wins': target_wins,
                'grid_size': grid_size,
                'difficulty': settings.get('difficulty', 'medium'),
                'description': f'Win {target_wins} game(s) vs AI',
            }

        elif challenge_type == 'coding':
            difficulty = settings.get('difficulty', 'easy')
            history = (room or {}).get('coding_problem_history', [])
            try:
                problem = await asyncio.wait_for(
                    asyncio.to_thread(generate_coding_problem, difficulty, history),
                    timeout=8.0
                )
            except asyncio.TimeoutError:
                problem = None
            if not problem:
                easy_fallbacks = [
                    "Write a C++ program that takes an integer N and prints all numbers from 1 to N that are divisible by 3.",
                    "Write a C++ program that reads two integers and prints the result of integer division and remainder.",
                    "Write a C++ program that takes an integer N and prints a right-angled triangle of asterisks N rows tall.",
                    "Write a C++ program that reads a character and prints whether it is a vowel or consonant.",
                    "Write a C++ program that takes a positive integer and prints the sum of its digits.",
                ]
                medium_fallbacks = [
                    "Write a C++ program that reads a sentence and counts how many words in it start with a vowel.",
                    "Write a C++ program that takes a string and prints it in reverse order without using library reverse functions.",
                    "Write a C++ program that takes an array of N integers and prints the second largest element.",
                    "Write a C++ program that generates and prints a multiplication table up to N×N.",
                    "Write a C++ program that reads a string and prints the frequency of each character.",
                ]
                hard_fallbacks = [
                    "Write a C++ program that takes a string and compresses it by replacing consecutive repeated chars with char+count.",
                    "Write a C++ program that generates all permutations of a given string without using next_permutation.",
                    "Write a C++ program that implements a simple encrypt/decrypt using Caesar cipher with a shift of 3.",
                    "Write a C++ program that takes a mathematical expression with + and - operators and evaluates it.",
                    "Write a C++ program that finds the longest palindromic substring in a given string.",
                ]
                pool = {'easy': easy_fallbacks, 'medium': medium_fallbacks, 'hard': hard_fallbacks}
                pool = pool.get(difficulty, easy_fallbacks)
                available = []
                for p in pool:
                    if p not in history:
                        available.append(p)
                if not available:
                    available = pool
                problem = random.choice(available)
            if room is not None:
                history.append(problem)
                if len(history) > 5:
                    history.pop(0)
                room['coding_problem_history'] = history
                cache.set(f'room_{self.room_code}', room, timeout=3600)
            return {
                'type': 'coding',
                'problem': problem,
                'description': problem,
                'difficulty': difficulty,
            }


# Generates quiz questions for multiplayer. Tries the AI fallback chain
# (groq -> gemini -> openrouter), then falls back to the local offline
# bank so quiz rooms still start on hosts with no AI keys (e.g. Render).
# If removed, multiplayer quiz questions can never be generated.
    async def _generate_quiz_questions(self, topic, count):
        topics_map = {
            'gk': 'general knowledge (countries, history, science, geography)',
            'tech': 'technology, AI, programming, full forms, computer science',
            'nepali_riddles': 'simple Nepal GK questions written in Nepali Devnagari script — plain knowledge questions only',
            'riddles': 'fun easy trivia questions with one clear answer',
            'nepal': 'Nepal (history, geography, culture, famous figures)',
            'mixed': 'mix of general knowledge, technology, trivia, world facts, and Nepal GK',
        }
        topic_desc = topics_map.get(topic, 'general knowledge')
        is_nepali = topic == 'nepali_riddles'
        prompt = f"""Generate {count} multiple-choice quiz questions about {topic_desc}.
Each question MUST be a JSON object with these exact keys:
- "question": the question text (string)
- "options": an array of exactly 4 answer choices (strings)
- "answer": the correct answer (string, must be one of the 4 options)
- "answer_en": the answer in simple English transliteration (string)
- "explanation": a brief 1-sentence explanation (string)
- "language": {"\"ne\" (write question and options in Nepali Devnagari with correct spelling)" if is_nepali else "\"en\""}
Rules:
- Every question must be straightforward with ONE clear meaning — NO double meanings, NO wordplay tricks, NO cheeky or suggestive content
- Make questions decent, fun and educational
- Exactly 4 unique options, answer must be one of the options
- Vary difficulty within the set
- Output ONLY a valid JSON array, no markdown, no prose"""
        result = None
        try:
            result = _groq_request([{'role': 'user', 'content': prompt}], model='llama3-8b-8192', temperature=0.9, max_tokens=4096)
            if not result:
                result = _groq_request([{'role': 'user', 'content': prompt}], temperature=0.9, max_tokens=4096)
            if not result:
                result = _gemini_request(prompt)
            if not result:
                result = _openrouter_request([{'role': 'user', 'content': prompt}], temperature=0.9, max_tokens=4096)
            questions = self._parse_quiz_questions(result)
            if questions:
                return questions
        except Exception:
            pass
        from .quiz_bank import get_local_questions
        return get_local_questions(topic, count)

# Parses and validates the AI quiz JSON response.
# If removed, malformed AI answers crash the quiz generator.
# Only used in _generate_quiz_questions.
    def _parse_quiz_questions(self, result):
        try:
            cleaned = result.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('\n', 1)[1]
                cleaned = cleaned.rsplit('```', 1)[0]
            questions = json.loads(cleaned.strip())
            if not isinstance(questions, list):
                raise ValueError('Not a list')
            for q in questions:
                for k in ('question', 'options', 'answer', 'explanation'):
                    if k not in q:
                        raise ValueError('Missing keys')
                if len(q['options']) != 4:
                    raise ValueError('Need exactly 4 options')
                if q['answer'] not in q['options']:
                    q['answer'] = q['options'][0]
            random.shuffle(questions)
            return questions
        except (json.JSONDecodeError, ValueError, KeyError):
            return None

    @database_sync_to_async
# Adds XP and coins to a player's account.
# If removed, players never get rewards.
# Runs in a thread from _send_game_over.
    def _award_xp_coins(self, user_id, xp, coins):
        try:
            user = User.objects.get(id=user_id)
            user.xp += int(xp * (1 + user.xp_boosts * 0.5))
            user.coins += coins
            new_level = user.xp // 1000 + 1
            if new_level > user.level:
                user.coins += 50
                user.level = new_level
            user.save(update_fields=['xp', 'coins', 'level'])
        except User.DoesNotExist:
            pass

# Makes a clean copy of the player list for sending out.
# If removed, raw player data leaks in messages.
# Used in many broadcast messages.
    def _sanitize_players(self, players):
        sanitized = []
        for p in players:
            sanitized.append({
                'user_id': p['user_id'],
                'username': p['username'],
                'display_name': p.get('display_name', p['username']),
                'avatar': p.get('avatar', ''),
                'level': p.get('level', 1),
                'rank': p.get('rank', 'Beginner'),
                'is_ready': p.get('is_ready', False),
                'connected': p.get('connected', False),
            })
        return sanitized

# Sends the player list update to this websocket.
# If removed, players won't see lobby changes.
# Called by the channel layer group broadcast.
    async def player_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_update',
            'players': event['players'],
            'status': event['status'],
        }))

# Sends a countdown number to this websocket.
# If removed, players see no countdown.
# Called by the channel layer group broadcast.
    async def countdown_tick(self, event):
        await self.send(text_data=json.dumps({
            'type': 'countdown',
            'count': event['count'],
        }))

# Sends the challenge data when the game begins.
# If removed, the game never starts for this player.
# Called by the channel layer group broadcast.
    async def challenge_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'challenge_start',
            'challenge': event['challenge'],
            'challenge_type': event['challenge_type'],
            'players': event['players'],
        }))

# Sends the reset room state to this websocket.
# If removed, Play Again won't reset the client.
# Called by the channel layer group broadcast.
    async def room_reset(self, event):
        await self.send(text_data=json.dumps({
            'type': 'room_reset',
            'players': event.get('players', []),
            'challenge_type': event.get('challenge_type', 'typing'),
            'custom_settings': event.get('custom_settings'),
        }))

# Sends a game-start failure to this websocket so clients return to the lobby.
# If removed, players hang on a stalled "Starting game" screen.
# Called by the channel layer group broadcast from begin_countdown.
    async def room_error(self, event):
        await self.send(text_data=json.dumps({
            'type': 'room_error',
            'message': event.get('message', 'Could not start the game.'),
        }))

# Sends an opponent's progress update to this websocket.
# If removed, opponents can't see each other.
# Called by the channel layer group broadcast.
    async def opponent_progress(self, event):
        if event['from_user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'opponent_progress',
                'progress': event['progress'],
                'from_user_id': event['from_user_id'],
                'from_username': event['from_username'],
            }))

# Sends the final game result to this websocket.
# If removed, players never see the result screen.
# Called by the channel layer group broadcast.
    async def game_over(self, event):
        await self.send(text_data=json.dumps(event))
