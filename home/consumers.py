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
from home.ai_service import check_cpp_code, generate_coding_problem

User = get_user_model()


def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


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

    async def disconnect(self, close_code):
        room = cache.get(f'room_{self.room_code}')
        if room:
            for p in room['players']:
                if p['user_id'] == self.user.id:
                    p['connected'] = False
                    break

            if room['status'] == 'active':
                # For scored games (typing, quiz), if both submitted or remaining player already submitted, resolve now
                scored_games = {'typing': ('typing_results', self._resolve_typing_winner), 'quiz': ('quiz_results', self._resolve_quiz_winner)}
                ct = room.get('challenge_type', '')
                if ct in scored_games:
                    rkey, resolver = scored_games[ct]
                    if rkey in room:
                        if str(self.user.id) in room[rkey] and len(room[rkey]) >= 2:
                            asyncio.create_task(resolver(room))
                            cache.set(f'room_{self.room_code}', room, timeout=3600)
                            return
                        other = next((p for p in room['players'] if p['user_id'] != self.user.id), None)
                        if other and str(other['user_id']) in room[rkey]:
                            asyncio.create_task(resolver(room))
                            cache.set(f'room_{self.room_code}', room, timeout=3600)
                            return

                room['disconnected_player_id'] = self.user.id
                room['disconnect_time'] = time.time()
                cache.set(f'room_{self.room_code}', room, timeout=3600)

                async def forfeit_after_delay():
                    await asyncio.sleep(10)
                    current_room = cache.get(f'room_{self.room_code}')
                    if current_room and current_room.get('disconnected_player_id') == self.user.id and current_room['status'] == 'active':
                        # Don't forfeit if disconnected player already submitted a scored result
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
                all_disconnected = all(not p['connected'] for p in room['players'])
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

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'ready':
            await self.handle_ready(data)
        elif msg_type == 'progress_update':
            await self.handle_progress_update(data)
        elif msg_type == 'challenge_complete':
            await self.handle_challenge_complete(data)
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

    async def handle_reset_room(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room:
            return
        is_creator = room['players'] and room['players'][0]['user_id'] == self.user.id
        if not is_creator:
            return
        room['status'] = 'waiting'
        room.pop('challenge', None)
        for p in room['players']:
            p['is_ready'] = False
        cache.set(f'room_{self.room_code}', room)
        for p in room['players']:
            if p['connected']:
                await self.channel_layer.send(
                    p['channel_name'],
                    {
                        'type': 'room_reset',
                        'players': [{
                            'user_id': pl['user_id'],
                            'username': pl['username'],
                            'display_name': pl.get('display_name', pl['username']),
                            'avatar': pl.get('avatar', ''),
                            'level': pl.get('level', 1),
                            'rank': pl.get('rank', 'Beginner'),
                            'is_ready': pl.get('is_ready', False),
                            'connected': pl.get('connected', False),
                        } for pl in room['players']],
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

    async def handle_update_challenge_type(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room:
            return
        is_creator = room['players'] and room['players'][0]['user_id'] == self.user.id
        if not is_creator:
            return
        new_type = data.get('challenge_type')
        if new_type not in ('typing','quiz','cps','aim3d','reaction','memory','runner','tictactoe'):
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

    async def challenge_type_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'challenge_type_update',
            'challenge_type': event['challenge_type'],
        }))

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

    async def settings_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'settings_update',
            'settings': event['settings'],
        }))

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

        all_ready = all(p['is_ready'] for p in room['players'])
        if all_ready and len(room['players']) >= 2 and room['status'] == 'waiting':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'begin_countdown', 'challenge_type': room['challenge_type']}
            )

    async def handle_start_countdown(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] != 'waiting':
            return
        all_ready = all(p['is_ready'] for p in room['players'])
        if all_ready and len(room['players']) >= 2:
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'begin_countdown', 'challenge_type': room['challenge_type']}
            )

    async def begin_countdown(self, event):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] != 'waiting':
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

        challenge_type = event.get('challenge_type', 'typing')
        settings = room.get('custom_settings', {})
        challenge_data = await self._generate_challenge(challenge_type, settings, room)
        if challenge_data is None:
            challenge_data = {
                'type': 'typing',
                'passage': 'The quick brown fox jumps over the lazy dog.',
                'target_wpm': 40,
                'duration': 30,
            }

        room = cache.get(f'room_{self.room_code}')
        if not room:
            return
        room['status'] = 'active'
        room['challenge'] = challenge_data
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

    async def handle_progress_update(self, data):
        room = cache.get(f'room_{self.room_code}')
        if not room or room['status'] != 'active':
            return

        sender = None
        for p in room['players']:
            if p['user_id'] == self.user.id:
                sender = p
                break

        for p in room['players']:
            if p['user_id'] != self.user.id and p['connected']:
                await self.channel_layer.send(
                    p['channel_name'],
                    {
                        'type': 'opponent_progress',
                        'progress': data.get('progress', {}),
                        'from_user_id': self.user.id,
                        'from_username': sender['display_name'] if sender else self.user.username,
                    }
                )

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

        connected = [p for p in room['players'] if p['connected']]
        all_done = all(str(p['user_id']) in room[result_key] for p in connected)

        if not all_done:
            asyncio.create_task(self._scored_timeout_wait(self.room_code, result_key, resolver_method))
            return False
        return True

    async def _scored_timeout_wait(self, room_code, result_key, resolver_method):
        await asyncio.sleep(60)
        room = cache.get(f'room_{room_code}')
        if not room or room['status'] == 'finished':
            return
        if result_key not in room or len(room[result_key]) == 0:
            return
        await resolver_method(room)

    async def _handle_typing_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'typing_results', self._resolve_typing_winner)
        if ready:
            await self._resolve_typing_winner(room)

    async def _handle_quiz_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'quiz_results', self._resolve_quiz_winner)
        if ready:
            await self._resolve_quiz_winner(room)

    async def _handle_cps_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'cps_results', self._resolve_cps_winner)
        if ready:
            await self._resolve_cps_winner(room)

    async def _resolve_cps_winner(self, room):
        if 'cps_results' not in room or not room['cps_results']:
            return
            
        results = list(room['cps_results'].values())
        
        # Ensure CPS is properly converted to float and add for debugging
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))  # Ensure user_id is int
            # Try multiple field names for CPS value
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
        
        # Sort by: HIGHEST CPS first (descending), then LOWEST time (ascending)  
        results.sort(key=lambda r: (-r.get('cps_float', 0), r.get('time_float', 999999)))
        
        if not results:
            return
            
        # Pick the winner (should be highest CPS)
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

    async def _resolve_typing_winner(self, room):
        results = list(room['typing_results'].values())
        results.sort(key=lambda r: (-float(r.get('wpm', 0)), -float(r.get('accuracy', 0)), float(r.get('time', 0))))
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner['username']
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

    async def _resolve_quiz_winner(self, room):
        results = list(room['quiz_results'].values())
        results.sort(key=lambda r: (-int(r.get('score', 0)), float(r.get('completion_time') or 999999), int(r.get('total', 1))))
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner['username']
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

    async def _handle_aim3d_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'aim3d_results', self._resolve_aim3d_winner)
        if ready:
            await self._resolve_aim3d_winner(room)

    async def _handle_reaction_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'reaction_results', self._resolve_reaction_winner)
        if ready:
            await self._resolve_reaction_winner(room)

    async def _handle_memory_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'memory_results', self._resolve_memory_winner)
        if ready:
            await self._resolve_memory_winner(room)

    async def _handle_runner_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'runner_results', self._resolve_runner_winner)
        if ready:
            await self._resolve_runner_winner(room)

    async def _handle_tictactoe_complete(self, room, data):
        ready = await self._store_result_and_check(room, data, 'tictactoe_results', self._resolve_tictactoe_winner)
        if ready:
            await self._resolve_tictactoe_winner(room)

    async def _resolve_aim3d_winner(self, room):
        if 'aim3d_results' not in room or not room['aim3d_results']:
            return
        results = list(room['aim3d_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['score_float'] = float(r.get('current_score') or r.get('score', 0))
            r['time_float'] = float(r.get('completion_time') or 999999)
        results.sort(key=lambda r: (-r.get('score_float', 0), r.get('time_float', 999999)))
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

    async def _resolve_reaction_winner(self, room):
        if 'reaction_results' not in room or not room['reaction_results']:
            return
        results = list(room['reaction_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['avg_float'] = float(r.get('avg_time') or r.get('avg', 9999))
            r['time_float'] = float(r.get('completion_time') or 999999)
        results.sort(key=lambda r: (r.get('avg_float', 9999), r.get('time_float', 999999)))
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

    async def _resolve_memory_winner(self, room):
        if 'memory_results' not in room or not room['memory_results']:
            return
        results = list(room['memory_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['level_int'] = int(r.get('level', r.get('current_level', 0)) or 0)
            r['time_float'] = float(r.get('completion_time') or 999999)
        results.sort(key=lambda r: (-r.get('level_int', 0), r.get('time_float', 999999)))
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

    async def _resolve_runner_winner(self, room):
        if 'runner_results' not in room or not room['runner_results']:
            return
        results = list(room['runner_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['score_float'] = float(r.get('score', r.get('current_score', 0)) or 0)
            r['time_float'] = float(r.get('completion_time') or 999999)
        results.sort(key=lambda r: (-r.get('score_float', 0), r.get('time_float', 999999)))
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

    async def _resolve_tictactoe_winner(self, room):
        if 'tictactoe_results' not in room or not room['tictactoe_results']:
            return
        results = list(room['tictactoe_results'].values())
        for r in results:
            r['user_id'] = int(r.get('user_id', 0))
            r['wins_int'] = int(r.get('wins', 0) or 0)
            r['time_float'] = float(r.get('completion_time') or 999999)
        results.sort(key=lambda r: (-r.get('wins_int', 0), r.get('time_float', 999999)))
        if not results:
            return
        winner = results[0]
        winner_id = winner['user_id']
        room['winner_id'] = winner_id
        room['winner_username'] = winner.get('username', 'Unknown')
        room['status'] = 'finished'
        cache.set(f'room_{self.room_code}', room, timeout=3600)
        await self._send_game_over(room, winner_id)

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
            # Extract primary and secondary scores based on game type
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

    async def _send_game_over(self, room, winner_id):
        fresh = cache.get(f'room_{self.room_code}')
        if fresh:
            room = fresh
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

        ctype = room.get('challenge_type', '')
        result_key_map = {
            'typing': 'typing_results', 'quiz': 'quiz_results',
            'cps': 'cps_results', 'reaction': 'reaction_results',
            'memory': 'memory_results', 'aim3d': 'aim3d_results',
            'runner': 'runner_results', 'tictactoe': 'tictactoe_results',
        }
        result_key = result_key_map.get(ctype)
        results = room.get(result_key, {}) if result_key else {}
        await asyncio.gather(*[
            asyncio.to_thread(
                self._update_game_stats,
                p['user_id'], ctype,
                results.get(str(p['user_id']), {}),
                p['user_id'] == winner_id,
            )
            for p in players if ctype
        ])

        # Determine result key from challenge_type to include final scores in game_over
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
        ctype = room.get('challenge_type', '')
        result_key = result_key_map.get(ctype)
        results = room.get(result_key, {}) if result_key else {}

        for p in room['players']:
            is_winner = p['user_id'] == winner_id
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
                    'xp': xp_winner if is_winner else xp_loser,
                    'coins': coins_winner if is_winner else coins_loser,
                    'xp_winner': xp_winner,
                    'coins_winner': coins_winner,
                    'xp_loser': xp_loser,
                    'coins_loser': coins_loser,
                    'self_result': self_result_data,
                    'opponent_result': opponent_result_data,
                    'all_results': results,
                }
            )

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
                        'xp': xp_winner if is_winner else xp_loser,
                        'coins': coins_winner if is_winner else coins_loser,
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
            QUIZ_BANK = {
                'general': [
                    {'q': 'What is the capital of France?', 'opts': ['London','Berlin','Paris','Madrid'], 'ans': 2},
                    {'q': 'How many continents are there?', 'opts': ['5','6','7','8'], 'ans': 2},
                    {'q': 'What color are bananas when ripe?', 'opts': ['Red','Green','Yellow','Blue'], 'ans': 2},
                    {'q': 'Which animal is known as the King of the Jungle?', 'opts': ['Tiger','Lion','Elephant','Bear'], 'ans': 1},
                    {'q': 'How many legs does a dog have?', 'opts': ['2','4','6','8'], 'ans': 1},
                    {'q': 'What do bees produce?', 'opts': ['Milk','Honey','Wax','Silk'], 'ans': 1},
                    {'q': 'Which planet is closest to the Sun?', 'opts': ['Venus','Mercury','Earth','Mars'], 'ans': 1},
                    {'q': 'What is the opposite of hot?', 'opts': ['Warm','Cool','Cold','Freezing'], 'ans': 2},
                    {'q': 'How many days in a week?', 'opts': ['5','6','7','8'], 'ans': 2},
                    {'q': 'What shape has 3 sides?', 'opts': ['Square','Circle','Triangle','Rectangle'], 'ans': 2},
                ],
                'science': [
                    {'q': 'What is H2O?', 'opts': ['Oxygen','Hydrogen','Water','Salt'], 'ans': 2},
                    {'q': 'What planet is known as the Red Planet?', 'opts': ['Venus','Mars','Jupiter','Saturn'], 'ans': 1},
                    {'q': 'What force keeps us on the ground?', 'opts': ['Magnetism','Friction','Gravity','Inertia'], 'ans': 2},
                    {'q': 'What gas do plants absorb?', 'opts': ['Oxygen','Nitrogen','CO2','Helium'], 'ans': 2},
                    {'q': 'What is the speed of light approx?', 'opts': ['300 km/s','300,000 km/s','3,000 km/s','30,000 km/s'], 'ans': 1},
                    {'q': 'What element is needed for fire?', 'opts': ['Nitrogen','Oxygen','Hydrogen','Carbon'], 'ans': 1},
                    {'q': 'What organ pumps blood?', 'opts': ['Lungs','Brain','Heart','Liver'], 'ans': 2},
                    {'q': 'What is the hardest natural substance?', 'opts': ['Gold','Iron','Diamond','Platinum'], 'ans': 2},
                    {'q': 'What planet has the most moons?', 'opts': ['Jupiter','Saturn','Uranus','Neptune'], 'ans': 1},
                    {'q': 'What type of rock is formed from lava?', 'opts': ['Sedimentary','Metamorphic','Igneous','Fossil'], 'ans': 2},
                ],
                'history': [
                    {'q': 'Who was the first US President?', 'opts': ['Adams','Jefferson','Washington','Lincoln'], 'ans': 2},
                    {'q': 'What year did WWII end?', 'opts': ['1943','1944','1945','1946'], 'ans': 2},
                    {'q': 'Which ancient civilization built pyramids?', 'opts': ['Greek','Roman','Egyptian','Persian'], 'ans': 2},
                    {'q': 'What ship sank on its maiden voyage in 1912?', 'opts': ['Lusitania','Titanic','Bismarck','Victory'], 'ans': 1},
                    {'q': 'Who discovered America in 1492?', 'opts': ['Vasco da Gama','Columbus','Magellan','Cook'], 'ans': 1},
                    {'q': 'What wall divided Berlin?', 'opts': ['Great Wall','Berlin Wall','Iron Wall',"Hadrian's Wall"], 'ans': 1},
                    {'q': 'Which empire was ruled by Genghis Khan?', 'opts': ['Ottoman','Roman','Mongol','Persian'], 'ans': 2},
                    {'q': 'What ancient wonder was in Babylon?', 'opts': ['Colossus','Hanging Gardens','Lighthouse','Temple'], 'ans': 1},
                    {'q': 'Who painted the Mona Lisa?', 'opts': ['Raphael','Michelangelo','Da Vinci','Donatello'], 'ans': 2},
                    {'q': 'What civilization invented the wheel?', 'opts': ['Egyptian','Greek','Mesopotamian','Chinese'], 'ans': 2},
                ],
                'technology': [
                    {'q': 'What does CPU stand for?', 'opts': ['Central Process Unit','Central Processing Unit','Computer Process Unit','Core Processing Unit'], 'ans': 1},
                    {'q': 'Who founded Microsoft?', 'opts': ['Jobs','Gates','Zuckerberg','Musk'], 'ans': 1},
                    {'q': 'What does HTML stand for?', 'opts': ['HyperText Markup Language','HighText Machine Language','HyperTool Markup Language','HomeTool Markup Language'], 'ans': 0},
                    {'q': 'What is 8 bits called?', 'opts': ['Kilobyte','Megabyte','Byte','Gigabyte'], 'ans': 2},
                    {'q': 'What programming language is used for iOS apps?', 'opts': ['Java','Kotlin','Swift','Dart'], 'ans': 2},
                    {'q': 'What does RAM stand for?', 'opts': ['Read Access Memory','Random Access Memory','Run Access Mode','Read All Memory'], 'ans': 1},
                    {'q': 'What year was the iPhone first released?', 'opts': ['2005','2006','2007','2008'], 'ans': 2},
                    {'q': 'What does CSS style?', 'opts': ['Structure','Content','Design','Data'], 'ans': 2},
                    {'q': 'What protocol powers the web?', 'opts': ['FTP','SMTP','HTTP','TCP'], 'ans': 2},
                    {'q': 'What is Python?', 'opts': ['Snake','Game','Programming Language','Database'], 'ans': 2},
                ],
                'riddles': [
                    {'q': 'What has keys but can\'t open locks?', 'opts': ['A map','A piano','A computer','A book'], 'ans': 1},
                    {'q': 'What can travel around the world while staying in a corner?', 'opts': ['A stamp','A plane','A ship','A car'], 'ans': 0},
                    {'q': 'What gets wetter the more it dries?', 'opts': ['A sponge','A towel','A mop','Rain'], 'ans': 1},
                    {'q': 'What has a head and a tail but no body?', 'opts': ['A snake','A coin','A needle','A pencil'], 'ans': 1},
                    {'q': 'What has hands but can\'t clap?', 'opts': ['A statue','A clock','A mannequin','A doll'], 'ans': 1},
                    {'q': 'What can you break even if you never pick it up?', 'opts': ['A promise','A glass','A record','A bone'], 'ans': 0},
                    {'q': 'What goes up but never comes down?', 'opts': ['A balloon','Smoke','Age','A rocket'], 'ans': 2},
                    {'q': 'What has a neck but no head?', 'opts': ['A giraffe','A bottle','A shirt','A guitar'], 'ans': 1},
                    {'q': 'What building has the most stories?', 'opts': ['A skyscraper','A library','A museum','A theater'], 'ans': 1},
                    {'q': 'What can you catch but not throw?', 'opts': ['A ball','A fish','A cold','A frisbee'], 'ans': 2},
                ],
                'gk': [
                    {'q': 'What is the largest ocean on Earth?', 'opts': ['Atlantic','Indian','Arctic','Pacific'], 'ans': 3},
                    {'q': 'What is the longest river in the world?', 'opts': ['Amazon','Nile','Mississippi','Yangtze'], 'ans': 1},
                    {'q': 'Which country has the largest population?', 'opts': ['USA','India','China','Indonesia'], 'ans': 1},
                    {'q': 'What is the tallest mountain in the world?', 'opts': ['K2','Everest','Kangchenjunga','Lhotse'], 'ans': 1},
                    {'q': 'Which planet is known as the Morning Star?', 'opts': ['Mars','Venus','Mercury','Jupiter'], 'ans': 1},
                    {'q': 'What is the smallest country in the world?', 'opts': ['Monaco','Vatican City','San Marino','Liechtenstein'], 'ans': 1},
                    {'q': 'Which language has the most native speakers?', 'opts': ['English','Mandarin','Spanish','Hindi'], 'ans': 1},
                    {'q': 'What is the largest desert in the world?', 'opts': ['Sahara','Arabian','Gobi','Antarctic'], 'ans': 3},
                    {'q': 'Which country invented paper?', 'opts': ['Japan','India','China','Egypt'], 'ans': 2},
                    {'q': 'What is the most abundant gas in Earth\'s atmosphere?', 'opts': ['Oxygen','CO2','Nitrogen','Hydrogen'], 'ans': 2},
                ],
                'gau_hani_katha': [
                    {'q': 'In Nepali folklore, what is a "Gau" traditionally?', 'opts': ['A river','A village','A mountain','A temple'], 'ans': 1},
                    {'q': 'What is "Hani Katha" in Nepali tradition?', 'opts': ['A sad story','A joke tale','A folk tale','A war story'], 'ans': 2},
                    {'q': 'Which animal is sacred in Nepali culture?', 'opts': ['Cow','Tiger','Elephant','Peacock'], 'ans': 0},
                    {'q': 'What is the traditional Nepali greeting?', 'opts': ['Namaste','Salam','Hello','Jai Nepal'], 'ans': 0},
                    {'q': 'Which flower is the national flower of Nepal?', 'opts': ['Lotus','Rhododendron','Marigold','Rose'], 'ans': 1},
                    {'q': 'What is the main festival of Nepal?', 'opts': ['Diwali','Dashain','Tihar','Holi'], 'ans': 1},
                    {'q': 'What is "Momo" in Nepali cuisine?', 'opts': ['Bread','Dumpling','Rice','Curry'], 'ans': 1},
                    {'q': 'Which mountain is known as "Sagarmatha" in Nepal?', 'opts': ['K2','Everest','Annapurna','Lhotse'], 'ans': 1},
                    {'q': 'What is the traditional Nepali topi called?', 'opts': ['Pagri','Topi','Dhaka','Pheta'], 'ans': 1},
                    {'q': 'Which animal is believed to be the vehicle of Lord Shiva?', 'opts': ['Elephant','Bull','Peacock','Lion'], 'ans': 1},
                ],
            }
            topic = settings.get('topic', 'mixed')
            question_count = settings.get('question_count', 5)
            if topic == 'mixed':
                topic = random.choice(list(QUIZ_BANK.keys()))
            if topic not in QUIZ_BANK:
                topic = random.choice(list(QUIZ_BANK.keys()))
            available = QUIZ_BANK[topic]
            count = min(question_count, len(available))
            questions = random.sample(available, count)
            return {
                'type': 'quiz',
                'topic': topic,
                'questions': questions,
                'question_count': count,
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
                available = [p for p in pool if p not in history]
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

        return None

    @database_sync_to_async
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

    def _sanitize_players(self, players):
        return [
            {
                'user_id': p['user_id'],
                'username': p['username'],
                'display_name': p.get('display_name', p['username']),
                'avatar': p.get('avatar', ''),
                'level': p.get('level', 1),
                'rank': p.get('rank', 'Beginner'),
                'is_ready': p.get('is_ready', False),
                'connected': p.get('connected', False),
            }
            for p in players
        ]

    async def player_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_update',
            'players': event['players'],
            'status': event['status'],
        }))

    async def countdown_tick(self, event):
        await self.send(text_data=json.dumps({
            'type': 'countdown',
            'count': event['count'],
        }))

    async def challenge_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'challenge_start',
            'challenge': event['challenge'],
            'challenge_type': event['challenge_type'],
            'players': event['players'],
        }))

    async def room_reset(self, event):
        await self.send(text_data=json.dumps({
            'type': 'room_reset',
            'players': event.get('players', []),
            'challenge_type': event.get('challenge_type', 'typing'),
            'custom_settings': event.get('custom_settings'),
        }))

    async def opponent_progress(self, event):
        if event['from_user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'opponent_progress',
                'progress': event['progress'],
                'from_user_id': event['from_user_id'],
                'from_username': event['from_username'],
            }))

    async def game_over(self, event):
        await self.send(text_data=json.dumps(event))
