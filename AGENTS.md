# Multiplayer Arena — Development Log

## Goal
- Build a complete real-time multiplayer arena with full challenge customization, chat invites, social sharing, correct reward distribution, modernized inventory/shop UI, and reliable WebRTC calling.
- Rewrite typing games to Monkeytype-style character-level typing with real-time opponent cursor tracking and compact lobby layout.

## Constraints & Preferences
- Text must appear directly on canvas via contentEditable, not overlay
- Style changes (font, color, size, outline/neon) must work mid-edit without losing typed text
- Resize handle (bottom-right), rotate handle (top-center) — Canva-style
- Music uses Jamendo API (no YouTube); segment trimmer for start/end
- Upload layers resize (aspect-ratio locked), rotate, drag, delete
- Story viewer plays music as separate audio element, progress bar animates over segment duration
- Quick emoji reactions (❤️ 😂 😮 😢 😡 👍) with flying animation
- Friend requests must be mutual (accept/reject)
- Only enrolled users shown in search
- Voice/video calls use WebRTC with HTTP polling for signaling (no Django Channels)
- Social page must not look like Facebook — custom dark/neon theme, no 3-column layout, unique story cards, custom popups
- Multiplayer must use real-time WebSocket (Django Channels) with room codes, countdown, live progress sync, XP/coins rewards, and per-game customization
- Invite popup must appear site-wide regardless of which page the user is on
- Currency bar (cash + gems) must match reference UI with actual images
- Inventory animations must be subtle and clean — not over-the-top or distracting
- **Multiplayer games must load the exact original game code** in an iframe, not separate React re-implementations
- Typing passages must be lowercase only, no symbols or capital letters (a-z + spaces)
- Character-level continuous typing (not word-by-word), hidden textarea, backspace support
- Opponent cursor: faded/animated vertical bar tracking opponent's real-time word+char position
- Progress bars at top centre: own (gold) + opponent (blue, 60% opacity)
- Body must allow vertical scrolling (not `overflow:hidden`) so lobby content fits at 100% zoom
- Cursor must auto-refocus on any keystroke (not just click on words-box)

## Progress
### Done
- **All 9 original game files restored** (`templates/games/*.html`) — all multiplayer code (mpRoom/mpWs/mpMode/connectMultiplayer/showMpGameOver/mpGameOver divs/multiplayer object/game logic overrides) completely stripped from every file: aim3d, cps, fitness, memory, quiz, reaction, runner, tictactoe, typing. Each file is 100% clean standalone.
- **All 9 multiplayer game templates created** (`templates/games/multiplayer/*.html`) — copies of originals + opponent tracking overlay + postMessage API. Each template has:
  - Opp-tracker CSS (opp-tracker fixed panel)
  - Opp-tracker HTML (after `<body>`)
  - `sendProgress(data)` / `sendComplete(data)` functions using `window.parent.postMessage`
  - `message` event listener handling `opponent_progress` updates and `start` signal
  - `ready` signal sent on load via `window.parent.postMessage({type:'ready'}, '*')`
- **`multiplayer_game_view`** in `home/views.py` — renders `games/multiplayer/{game_name}.html` for valid game types
- **URL pattern** in `home/urls.py` — `multiplayer-game/<slug:game_name>/` → `multiplayer_game_view`
- **`ChallengeGame` iframe** in `multiplayer.html` — renders iframe pointing to `/multiplayer-game/${challengeType}/?room=...` with postMessage relay for progress/complete/opponent_progress
- **quiz.html fixed** — syntax error (stray `}` before `</script>`) corrected
- **typing.html fixed** — stray `}` on line 670 removed
- **Customization panel (ChallengeSettings component)** added to `multiplayer.html` — per-game parameter selectors for all 9 challenge types
- **Custom settings WebSocket flow** — `handle_update_settings` consumer handler; `sendSettings` in `useMultiplayerSocket`; `settings_update` broadcast
- **Quiz expanded** with 3 new categories in consumer's `_generate_challenge`
- **Quiz auto-advance** — 1.2s multiplayer, 1.5s standalone
- **Reward distribution fixed** — consumer sends personalized `game_over` via `channel_layer.send` with correct `won`/`xp`/`coins` per player
- **Multiplayer invite in chatx** — invite button + card rendering in chat messages
- **Share results** — `shareResult` posts to `/social/create/` with challenge type, win/loss, XP/coins
- **Invite popup notification** — `showInviteNotification`/`detectNewInvites` in chatx; full-screen modal, 30s auto-dismiss, duplicate suppression
- **Global invite polling** — `templates/invite_poll.html` + `{% include %}` before `</body>` in 22 templates (NOT in game files — only layout/dashboard templates); shared `window.seenInviteRoomCodes` + `window.declinedInvites` persisted in localStorage
- **WebRTC video call fixed** — `checkIncomingCalls` guard `if(pc||incomingCallerId)return;` prevents ICE/answer signal theft
- **Currency bar redesigned** — horizontal pills with `cash.png` and `diamond.png` images; values visible; links to shop
- **Diamond display fixed** — `diamonds: user.diamonds` replaces `soats:'0'` in both `dashboard_view` and `_player_context`
- **Inventory animations completely rewritten** — single `@keyframes softGlow`; no particles/emoji/scanlines; clean `fadeUp` card entrance
- **Bug: wrong challenge type (quiz → typing)** — consumers.py `handle_ready` was letting any player's ready signal overwrite the room's stored `challenge_type`; **Fix**: removed `room['challenge_type'] = data.get(...)` from `handle_ready`; removed `challenge_type` from React `sendReady` payload
- **Bug: 1 invite showing 5 popups** — **Fix**: both `invite_poll.html` and `chatx.html` now share `window.seenInviteRoomCodes` global set
- **Bug: black screen/gibberish on invite accept** — invite links pointed to `/multiplayer/room/CODE/` (JSON API endpoint). **Fix**: all invite links changed to `/multiplayer/?room=CODE`; added auto-join `useEffect` in `MultiplayerRoom`
- **Bug: missing avatar in invite popups** — **Fix**: both `showInvPopup` and `showInviteNotification` now accept `senderId`/`hasAvatar`; avatar HTML displayed via `/api/shop/avatar/?user_id=X` or fallback initial circle
- **Bug: popup keeps coming back after decline** — **Fix**: `invite_poll.html` now uses/restores `window.declinedInvites` from `localStorage('chatx_declined')`; Decline button saves to both `seenInviteCodes_`+uid and `chatx_declined` localStorage keys
- **Bug: accept invite shows disconnected / room not found** — **Fix**: `sendInviteMessage` now redirects creator to `/multiplayer/?room=CODE`; `roomCode` starts empty in React (WebSocket only connects after join); `multiplayer_join_room` returns success with room state even when user already in room
- **Bug: progress not real-time** — **Fix**: `handle_progress_update` changed from `group_send` to `channel_layer.send` targeting only the opponent's `channel_name`
- **Bug: creator selects CPS but friend starts typing** — auto-join `useEffect` read `data.challenge_type` but API returns it nested as `data.room.challenge_type`; chatx `inviteToArena` hardcoded `challenge_type:'typing'`. **Fix**: auto-join reads `data.room.challenge_type`; `inviteToArena` redirected to multiplayer page; `sendFriendInvite` uses current `roomCode` instead of creating a new room

### Done This Session
- **`home/consumers.py`**: All 5 typing passages cleaned to lowercase letters + spaces only
- **`templates/games/typing.html` (standalone)**: Complete rewrite from word-by-word → Monkeytype-style continuous typing with hidden textarea, character-level highlighting, backspace, WPM/RAW/ACC/TIME stats
- **`templates/games/multiplayer/typing.html` (multiplayer)**: Right-side opp-tracker removed; top-centre progress bars added; opponent cursor (faded pulsing vertical bar) with real-time positioning; `char_index` included in progress updates; `opponent_name` passed from parent
- **`templates/multiplayer.html`**: `ChallengeGame` now receives `players` + `userId` props; extract opp progress from map before sending to iframe; opponent_name injected into start challenge object
- **`home/views.py:multiplayer_join_room`**: Resets finished rooms when already-in-room user joins (HTTP fallback for page reloads)
- **`home/consumers.py`**: Added `handle_reset_room` WebSocket handler — creator sends `reset_room`, server broadcasts `room_reset` to all connected players with updated room state
- **Focus fix**: Both standalone and multiplayer typing games auto-focus hidden input on any keystroke via `document.addEventListener('keydown')`; `words-box onclick="focusInput()"` also wired
- **Cursor animations**: Own cursor (2.5px + `caretBlink` keyframes); opponent cursor (`oppPulse` animation fades in/out)
- **Opponent cursor positioning**: `char_index=0` → before first char of word; `char_index>0` → after typed chars; `words-box` has `position:relative`
- **Room reset UI**: `room_reset` handler in `handleWSMessage` transitions view back to room-lobby, clears gameOver/challenge; Play Again button calls `sendRaw({type:'reset_room'})`
- **`home/consumers.py`**: Added `async def room_reset(self, event)` channel layer handler to forward room_reset to WebSocket clients

### Blocked
- End-to-end testing (full invite-accept-play + reset-replay flow)

## Key Decisions
- Used `channel_layer.send` to individual `channel_name` instead of `channel_layer.group_send` for personalized `game_over` AND `opponent_progress` messages
- Invite poll in `invite_poll.html` uses shared `window.seenInviteRoomCodes` + `window.declinedInvites` (persisted in localStorage) — both scripts check the same global sets
- `roomCode` starts empty in MultiplayerRoom; WebSocket connects only after HTTP join succeeds (prevents race condition where consumer adds user before join API)
- `multiplayer_join_room` returns room state on "already in room" instead of 400 error — allows creator's auto-join to succeed gracefully
- Invite links changed to `?room=CODE` query param (not path-based `/room/CODE/`) to avoid hitting JSON endpoint
- `sendFriendInvite` uses current `roomCode` instead of creating a new room — eliminates mismatch between room creator is in vs room friend is invited to
- **Multiplayer games loaded as iframes** from `templates/games/multiplayer/` instead of inline React components — preserves exact original game UX; postMessage API separates game logic from WebSocket lifecycle
- **postMessage protocol**: iframe sends `{type:'ready'}` → parent sends `{type:'start'}` + `{type:'opponent_progress'}`; iframe sends `{type:'progress'}` → parent forwards to WebSocket; iframe sends `{type:'complete'}` → parent forwards to WebSocket; parent handles `game_over` overlay itself
- **Opponent progress data flow fixed**: parent extracts `onOpponentProgress[oppUserId]` instead of sending the full `{userId: progress}` map to the iframe
- **Room reset uses WebSocket** (not HTTP) so all players receive reset simultaneously
- **Character-level typing** uses hidden textarea with `input` event listener (not keydown) for reliable backspace/IME handling
- **Auto-focus on keydown** (not just click) ensures keystrokes always go to the hidden input

## Next Steps
- Test full invite-accept-play flow end-to-end
- Test progress sync in all 9 game types
- Verify reward display: winner sees 75 XP + 60 coins, loser sees 25 XP + 0 coins
- Test 8-player lobby (join with 8 accounts)
- Test two-player replay flow: Play Again → WebSocket reset → all players back to lobby

## Critical Context
- Consumer sends personalized game_over with fields: `won` (bool), `xp` (int), `coins` (int), `winner_id`, `winner_username`, `reason`, `xp_winner`/`xp_loser`/`coins_winner`/`coins_loser` (backwards compat)
- `channel_layer.send` needs recipient's `channel_name` stored in room players — stored during WebSocket `connect`
- `handle_progress_update` now sends to ALL other players' `channel_name` (not just one opponent)
- `handle_ready` no longer modifies `room['challenge_type']` — the room's stored type from creation is authoritative
- `invite_poll.html` restores `window.declinedInvites` from `localStorage('chatx_declined')`; shared with chatx.html
- Auto-join `useEffect` reads `data.room.challenge_type` (nested), not `data.challenge_type` (undefined)
- `multiplayer_game_view` serves `templates/games/multiplayer/{game}.html` without typing redirect
- Original game files in `templates/games/` are 100% clean — no multiplayer code whatsoever
- Multiplayer game templates in `templates/games/multiplayer/` are copies of originals + opponent tracking overlay + postMessage API
- iframe relay: parent listens for postMessage `progress`/`complete`; forwards opponent_progress updates to iframe via useEffect on `lastOpponentProgress` state
- `static/cash.png` and `static/diamond.png` are the currency bar icons (user-provided + downloaded)
- Inventory CSS has NO particles, NO floating emoji, NO scanlines, NO pseudo-element effects — all effects are softGlow only
- `handle_reset_room` requires `is_creator` check — only player 0 can reset the room
- `room_reset` channel layer handler broadcasts updated player list + challenge_type to all connected players
- Typing rewrite uses char_index (0=before first char, >0=after typed chars) for opponent cursor positioning
- Play Again button calls `sendRaw({type:'reset_room'})` — WebSocket message, not HTTP navigation

## Relevant Files
- `C:\Users\Dell\Desktop\OJT PROJECT\home\consumers.py`: personalized `game_over`, `handle_update_settings`, `_generate_challenge` with custom settings; `handle_ready` no longer overrides challenge_type; `handle_progress_update` uses `channel_layer.send` (not group_send) for real-time opponent sync; `handle_update_challenge_type` for creator mid-lobby type switching; `handle_reset_room` at line 180 for Play Again replay
- `C:\Users\Dell\Desktop\OJT PROJECT\home\views.py`: `multiplayer_join_room` returns success with room state when user already in room; resets finished rooms for replay fallback; `multiplayer_game_view` at line 2009 serving `templates/games/multiplayer/{game}.html`
- `C:\Users\Dell\Desktop\OJT PROJECT\home\urls.py`: route `/multiplayer-game/<slug:game_name>/` at line 37
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\multiplayer.html`: `sendReady` no longer sends `challenge_type`; auto-join reads `data.room.challenge_type`; `roomCode` starts empty; `loading` view; `sendFriendInvite` uses current `roomCode`; `ChallengeGame` renders iframe at `/multiplayer-game/...` with postMessage relay; challenge type picker added to room-lobby; `room_reset` handler transitions to lobby; Play Again calls `sendRaw({type:'reset_room'})`
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\dashboard\chatx.html`: `sendInviteMessage` redirects creator to `/multiplayer/?room=CODE`; `showInviteNotification` shows avatar; invite links use `?room=CODE`; `detectNewInvites` passes avatar data; `inviteToArena` redirects to `/multiplayer/`
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\invite_poll.html`: global invite-polling IIFE; uses shared `window.seenInviteRoomCodes` + `window.declinedInvites`; persists to localStorage; Decline saves to both sets; shows sender avatar; links use `?room=CODE`
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\dashboard\inventory.html`: completely rewritten CSS — all complex animations replaced with `softGlow`; no particles, no pseudo-element effects
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\dashboard\home.html`: currency bar (cash.png + diamond.png + + button), START → multiplayer
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\games\*.html`: **all 9 restored to originals** — zero multiplayer code
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\games\multiplayer\*.html`: **all 9 multiplayer templates** — copies of originals + opp-tracker overlay + postMessage API (sendProgress, sendComplete, message listener, ready signal)
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\games\typing.html`: Monkeytype-style rewrite — hidden textarea, character-level highlighting, backspace, WPM/RAW/ACC/TIME stats
- `C:\Users\Dell\Desktop\OJT PROJECT\templates\games\multiplayer\typing.html`: Opponent cursor (`renderOpponentCursor`), top-centre progress bars, auto-focus keydown listener
- `C:\Users\Dell\Desktop\OJT PROJECT\static\cash.png`, `C:\Users\Dell\Desktop\OJT PROJECT\static\diamond.png`: currency bar icons
