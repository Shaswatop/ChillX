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
- **BUG FIX — countdown race (rooms stuck at "Starting game")**: `begin_countdown` runs on EVERY player's consumer instance; a non-creator instance could set `room['status']='countdown'` before the creator's instance, making the creator's instance return on the `status != 'waiting'` guard and never generate/send `challenge_start` → room stalled forever (~35% of starts). **Fix**: moved the `is_creator` gate to the TOP of `begin_countdown` (before the status transition), so only the creator's instance ever runs the countdown + challenge generation. Removed the now-redundant mid-function `is_creator` check.
- **E2E reward verification COMPLETE — all 7 playable games** (`.playwright-mcp/mp_e2e_entry.js`): typing, quiz, reaction, cps, aim3d, runner, memory all verified end-to-end via dual-account Playwright — winner always sees `VICTORY +75 XP +60 COINS`, loser sees `DEFEAT +25 XP` (no coins). Game-start stalls resolved by the countdown fix (post-fix runs start first-try).
- **Final E2E run 2026-08-12**: single full pass — all 7 games `pass:true` (winner split A/B as expected, both reward states correct). One transient infra crash on cps (iframe lookup raced) was retried once and passed — no game re-runs.
- **BUG FIX — `TypeError: document.addEventListener(...) is not a function` on `/games/typing/`**: classic missing-semicolon-before-IIFE. The backspace keydown listener ended with `})` (no `;`) on line 406, and the header-toggle IIFE on line 408 starts with `(`, which suppresses ASI — so the parser read it as calling the *return value* of `document.addEventListener(...)` (= `undefined`) with the IIFE as an argument. Confirmed via CDP pause-on-exception (global scope only, line 408 col 1) + route-interception bisection (ANY `(`-leading statement at that spot threw; `var x=1;`, `function f(){}`, `0,(function(){})()` did not). **Fix**: added `;` after the `})`. All 9 standalone games now 0 pageerrors (only aim3d's pre-existing `scene is not defined` from the missing gun-model GLB remains) and 0 horizontal overflow at 390px.
- **Verified no same bug elsewhere**: grep across `templates/games/` and `templates/games/multiplayer/` — no other file has a line ending `)` immediately followed by a line starting `(`; other games use inline `<script>(function(){...})();</script>` (own statement, safe). memory.html line 190-191 is a function-declaration `}` (ASI trigger) — safe.

### Done This Session
- **BUG FIX — gaming challenges return 404 (root-caused + fixed)**: AI invents `poki:<name>` game keys (`super_mario_bros`, `chesscom`, `tetr.io`, `knife_hit`, `dunk_shot`, `geometry-dash-online`) and `fix_challenge_link` blindly built `https://poki.com/en/g/<slug>` from them → poki.com 404s for the player.
  - Added verified `POKI_SLUGS` whitelist (52 slugs confirmed HTTP 200 on poki.com) + `POKI_TITLE_PHRASES` keyword→slug map + `find_poki_slug()` in `home/challenge_catalog.py`
  - `fix_challenge_link` poki branch now ONLY builds a poki link when the slug verifies; otherwise falls through to in-app `detect_game_key` instead of emitting a dead URL
  - Updated `home/ai_service.py` prompt to restrict poki picks to the verified list (removed the `poki:knife_hit` bad example)
  - Fixed 7 existing DB rows: 871→chess, 874→geometry-dash, 877→tetris, 774/781→mr-bullet, 775→penalty-shooters-2, 602 (Super Mario) → in-app `runner` challenge with target 5. All now return 200 (verified via browser).
- **BUG FIX — runner game unplayable on mobile (canvas stretched, player not visible)**: `resizeCanvas` stretched the 800x500 canvas to fill `window.innerWidth/Height`, distorting the world so the player was invisible/off-screen on phones. **Fix** in both `templates/games/runner.html` + `templates/games/multiplayer/runner.html`: canvas now letterboxes (keeps 800x500 aspect, centered via `left`/`top`), plus `orientationchange` handler + `resizeCanvas` toggles the rotate-overlay on coarse-pointer portrait devices (forces landscape). Verified: portrait letterboxes 390x243 centered, landscape 624x390 with player on-screen, on-screen touch buttons move the player (x:60→287).

### Done This Session (2026-08-16 bug-fix pass)
- **BUG FIX — multiplayer quiz clicks dead / score always 0**: Django 6 LocMemCache **pickles on get** → every `cache.get` returns a fresh copy. `begin_countdown` called `_generate_challenge` (which set `room['quiz_answers']` on the copy), then re-fetched a fresh room (no `quiz_answers`) and `cache.set` overwrote it → `handle_answer` found no `quiz_answers`, returned early, no `answer_result` ever sent → buttons disabled forever, score 0. **Fix**: capture `quiz_answers` from the mutated copy and re-apply it to the fresh room before `cache.set`. Verified via dual-account Playwright: `answer_result` now flows back, score increments, auto-advance works.
- **BUG FIX — gaming challenges 404 (empty links)**: DB scan found 3 gaming rows with empty links (832/835 Tetris, 812 Vex 4). Added "vex" to `IN_APP_GAMES` runner detection + `POKI_TITLE_PHRASES`; re-fixed all 3. Re-verified: 0 gaming rows without links.
- **BUG FIX — multiplayer aim3d didn't autostart**: standalone iframe had `?autostart=1` but multiplayer iframe lacked it → menu screen instead of game. Added `autostart=1` to `templates/games/multiplayer/aim3d.html`. Also themed the fallback gun (GLB missing → silver/black complaint) to site teal in `static/aim-trainer/app.js`. Verified multiplayer aim3d starts directly.
- **BUG FIX — social page not scrollable on mobile**: story editor registered a global `document` touchmove listener that `preventDefault()`-ed EVERY touch even when no drag was active → blocked all native scrolling. **Fix**: only preventDefault when a drag is actually in progress. Also removed redundant `height:100vh` on `.social-wrap` (it had `position:fixed;top:104px;bottom:0` — the vh made it 104px taller than viewport). Verified touch-drag scrolls to 385px.
- **BUG FIX — settings page not scrollable on mobile**: `#app` wrapper div had NO CSS rule → broke the flex height chain so `.content-panel` grew instead of scrolling, and `body{overflow:hidden}` blocked page scroll. **Fix**: `#app{display:flex;flex-direction:column;height:100vh;overflow:hidden}`. Verified AI tab now scrolls via touch drag.
- **BUG FIX — story local music uploads never play after save**: used `URL.createObjectURL(file)` — a blob URL that dies on page reload; the dead URL was saved to the DB. **Fix**: convert uploaded audio to a base64 data URL (like images/videos already do) before saving. **Jamendo trending flaky (0 results on mobile networks)**: added 3× retry + fallback to `popularity_total` search so the music list is never empty. Verified 20 music items load.
- **BUG FIX — dashboard hides Store/Events on mobile**: `@media(max-width:600px){.left-panel{display:none}}` removed them entirely. **Fix**: left-panel is now a slide-in drawer with a hamburger `.menu-toggle` in the topbar (mobile-only) + backdrop; desktop unchanged (toggle hidden, panel at x=28). Verified open/close/backdrop/store-href on 390px.
- **FEATURE — video call shows avatar instead of black screen when camera off**: added `.call-remote-avatar` overlay inside `.call-videos` (`templates/call_components.html`); `pc.ontrack` in `static/script.js` now listens for remote video track mute/end events and toggles the avatar overlay; audio-only calls show avatar by default; PiP bubble shows avatar when camera off; `endCall` resets. Verified elements wired on /chatx/.
- **FEATURE — invite popup rethemed to site navy/teal**: `templates/invite_poll.html` used purple `#7c5cfc` gradient; chatx version was white. Both now use the site theme (`#134166→#0d3b66` gradient, `#4a9ec4` accents, teal Join button).
- **FEATURE — coding challenges: paste-code submit + AI hints**: challenge modal now has a 💻 Code tab (auto-selected for coding categories — frontend `isCoding` matches `cod`/`program`/`develop`/`script`, backend same in `challenge_submit`). New `check_submission_code()` in `home/ai_service.py` judges pasted code and replies with SHORT HINTS (never raw compiler errors). Verified: `def solve(): return "hello world"` → "your code is a great start... try adding more function examples" (8/10, passed).
- **BUG FIX — lobby chat send was broken (NameError)**: `home/views.py` used `time.time()` in `multiplayer_chat_send` but never imported `time` → every send 500'd. Added `import time`. Verified send returns `{ok:true}` and poll returns the message.
- **FEATURE — floating chat head quick reactions**: added a Quick row to `templates/chathead.html` — 5 emoji (❤️😂🔥👀😤) + 4 phrase chips (GG, Watch my next move 😏, Nice, You got this 💪) that send instantly to the room chat via `chQuickSend()`; hidden when no room code. Verified tapping GG posts "Good game! GG" to the room.
- **FEATURE — AI chat widget responsive**: `templates/ai_chat_widget.html` (injected by middleware on /challenges/ + quiz) was a fixed 360×520 panel that overflowed on mobile. Added `@media(max-width:640px)` → panel fills the screen (10px insets, 370×824 on a 390px phone); drag disabled on small screens (panel is fullscreen); touch drag added for the header. Verified fits on 390×844, desktop unchanged.

### Done This Session
- **BUG FIX — chat head dead on mobile**: `templates/chathead.html` — (1) drag handler `preventDefault()`ed on touchstart, killing the tap that opens the panel; now only touchmove blocks. (2) synthetic mousedown after a tap re-entered the drag handler and reset the suppress flag → panel opened then instantly closed; added touch-timestamp guard. (3) `chPoll` only ran while the panel was open so unread badges never updated; now polls always and only renders when open. Verified: tap opens panel, quick phrases send, badge shows unread count while closed.
- **BUG FIX — social page 8.5MB / 5.3s on mobile**: `home/views.py` inlined every post's base64 `proof_image` into the feed HTML. Added `social_post_image` endpoint (lazy-loaded via `data-src` in `templates/dashboard/social.html`) — HTML dropped 8.5MB→332KB, DOMContent 5.3s→248ms. Fixed endpoint bug: `data[:20].find(';base64,')` slice was too short to ever match (prefix starts at index 14, needs 23 chars) → every image 400'd; now checks the full string + pads base64. All 42 post images verified 200.
- **BUG FIX — challenges page blocked 25s on first daily visit**: `home/views.py` called `auto_generate_daily(user)` synchronously (Groq AI batch gen) before rendering. Now runs in a daemon thread with a cache lock (only one request fires it); page renders instantly with a "Generating Your Challenges…" state that polls and auto-reloads. Verified: DOMContent 25s→52ms, auto-reload lands 3 cards.
- **FEATURE — .m4a story music support**: `templates/dashboard/social.html` — added `sePlayableUrl()` that converts base64 `data:` URLs to Blob object URLs for playback (iOS Safari can't play large data URLs in audio elements — m4a files are bigger than mp3s, so local music silently failed on iPhone). Used in story viewer + preview + add-to-story; blob URLs revoked on stop. Added explicit m4a/aac/flac MIME types to the upload `accept` + placeholder. Verified full flow: upload → add → share → reload → play (readyState 4, blob URL).
- **BUG FIX — quiz tie crowned a random winner (0-0 gave one player VICTORY)**: `home/consumers.py` `_resolve_quiz_winner` now collects ALL players sharing the top score into `winner_ids`; `_send_game_over` awards winner XP/coins to everyone in `winner_set` and sends `is_tie`/`winner_ids`; `static/js/multiplayer.js` trusts the server `won` flag and shows a DRAW badge. Verified E2E: both players see DRAW "everyone wins this round", both get +75 XP / +60 coins.
- **BUG FIX — challenge type change to Coding didn't stick (old challenge loaded)**: `home/consumers.py` `handle_update_challenge_type` whitelist was `('typing','quiz','cps','aim3d','reaction','memory','runner','tictactoe')` — **`coding` was missing**, so the server rejected the change and the room kept the previous type. Added `'coding'`. Verified E2E: creator picks Coding → both players start the C++ challenge with a code editor.
- **BUG FIX — runner not full-screen on mobile + slow summary**: `templates/games/runner.html` + `templates/games/multiplayer/runner.html` — `100vh` includes the browser URL bar/ribbon on phones so the canvas centered partly off-screen; switched to `100dvh` + `visualViewport` in `resizeCanvas`. Death→overlay delay cut 600ms→250ms. Verified: canvas fills the full 390px viewport height, death overlay shows at ~305ms, win triggers at the flag in ~39ms.

### Done This Session
- **BUG FIX — calling a user with no message history crashed the call**: `static/script.js` `startCall` did `name[0].toUpperCase()` where `name` came from `chatHeaderName`, which is only populated when messages exist → `TypeError: Cannot read properties of undefined` before the call even started. Fixed: `openChat` in `templates/dashboard/chatx.html` now sets the header name from the conversation item (always present), and `startCall` guards empty names. Verified E2E: call to a never-messaged user works.
- **BUG FIX — camera-off avatar never showed**: WebRTC does NOT fire a `mute` event on the receiver when the sender sets `enabled=false` (sender just transmits black frames — the track stays live), so the avatar overlay never appeared when a peer toggled the camera. Fixed: `callToggleCam` now sends an explicit `cam:on/off` signal via the polling channel; `pollCallSignals` handles `cam` to show/hide `callRemoteAvatar`; `send_call_signal` accepts the new `'cam'` type. Verified: camera off → avatar shows, camera on → avatar hides.
- **BUG FIX — avatar leaked into next call after hangup**: stopping the remote stream fires `onended` asynchronously, whose `updateRemoteAvatar()` re-added the `show` class after `endCall` removed it (invisible with the overlay closed, but would appear at the start of the next call). Fixed: `updateRemoteAvatar` now bails out (removes `show`) when no call is active, and `endCall` clears streams before hiding the avatar. Verified: after hangup the avatar class is clean.
- **BUG FIX — stale "Calling..." after call ended**: `endCall` never reset `callStatus`, so the caller's UI kept showing "Calling..." after the overlay closed. Now set to "Call ended".
- **Calls verified E2E**: two headless Chromes with fake media — A calls B (video), B sees incoming popup with caller name, accepts, both reach `Connected`, remote video renders on A, hang-up ends both sides, decline closes B's popup and A's overlay + releases A's local stream.

### Done This Session
- **Render shop-empty diagnosed**: seeds only run via `preDeployCommand` in `render.yaml` (migrate + seed_shop + seed_achievements). Verified `seed_shop` works on a fresh DB (69 items + raffle). Fix for a live service: run the commands in the Render Shell tab (or re-apply Blueprint). Local DB has 70 shop items, 46 gaming challenges, 366 total challenges.
- **FEATURE — quiz works offline (no AI keys)**: `/quiz/generate-questions/` and multiplayer `_generate_quiz_questions` were AI-only → 503/None on Render without keys. Added `home/quiz_bank.py` offline bank; both endpoints now fall back to `get_local_questions(topic, count)` when all AI providers fail (AI-first, Groq primary — no hardcoded-primary).
- **REWRITE — quiz content: NO double meanings, NO roasts**: `quiz_bank.py` rewritten — `_RIDDLES` puns replaced with `_TRIVIA` (simple one-clear-answer trivia), `_NEPALI_RIDDLES` Gau Khane Katha replaced with `_NEPALI_GK` (plain Nepal GK in Devnagari); taunt fields removed everywhere. AI prompts in `views.py quiz_generate_questions` + `consumers.py _generate_quiz_questions` rewritten: topics_map now describes riddles as fun easy trivia and nepali_riddles as simple Nepal GK Devnagari; added rule "NO double meanings, NO wordplay tricks, NO cheeky or suggestive content"; removed all taunt_correct/taunt_wrong requirements and examples.
- **REMOVED — roast/"regret mode" toggle from quiz UI**: stripped ALL taunt code from `templates/games/quiz.html` + `templates/games/multiplayer/quiz.html` (taunt CSS, topbar toggle label, tauntText div, 😈 popup + overlay HTML, popup JS handlers, per-answer taunt show/hide lines, `msg.taunt` handling in multiplayer answer_result). Topic button "गाउँखाने कथा" relabeled to "नेपाली ज्ञान" in both pickers + reveal labels. Cleaned dead taunt passthroughs in `home/consumers.py` (`answer_result`, `quiz_answers`, challenge gen).
- **Verified**: py_compile clean on consumers/views/quiz_bank; mocked no-key endpoint test returns 200 + 10 valid questions, taunt-free, for all 6 topics (gk, tech, nepal, riddles, nepali_riddles, mixed).

### Blocked
- Nothing — core multiplayer flow verified. (Remaining untested: invite-accept flow, 8-player lobby, reset-replay flow — see Next Steps.)

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
- **Runner — no pits, enemies are the only death source** (user request: "no void... only way player dies is from enemies and fix that enemy following mario position") in both `templates/games/runner.html` + `templates/games/multiplayer/runner.html`:
  - Level grounds made continuous (no falling gaps): L1 `[[0,90,23],[0,90,24]]` (flag at tile 85 well within), L2 `[[0,82,...]]` (flag tile 79), L3+L4 `[[0,77,...]]` (flag tile 75) — all extend past the flag
  - All `ai:'chaser'` enemies → `ai:'patrol'` (no homing onto Mario); removed the dead chaser AI branch in update() and the chaser marker in draw()
  - Verified in browser: player never falls below ground (maxY 440 vs ground 460); win triggers at flag (x 1700); multiplayer loads with continuous ground + patrol-only enemies

### Done This Session
- **NO-API-KEY MODE — the site fully works without any AI keys**: added `local_generate_challenges()` in `home/challenge_catalog.py` (builds a daily batch from verified in-app games, Poki slugs, Programiz compilers, and Kleki art — templates rotate per day, feed through `fix_challenge_link`/`validate_challenge` so every challenge gets a working link + scaled target). Wired as the last-resort fallback in `ai_service.generate_challenges` (both the early `return None` and the parse-failure path now fall through to it), so `auto_generate_daily`, `generate_more`, and the streaming loader all produce challenges with zero keys. Added `_local_chat_reply()` — keyword-based friendly chat replies (hi/challenge/hint/game/thanks/who-are-you) so the AI widget answers without a key. Added empty-key guards to `_gemini_request`, `_openrouter_request`, `_groq_request_stream` (already in `_groq_request`) so no-key mode makes zero network calls. Submission judges (text/image/code) already had benefit-of-the-doubt no-key fallbacks — verified. **Verified**: fresh user with all keys empty → daily batch of 3-8 challenges with working links (Programiz/Poki/in-app), stream + non-stream both work, chat replies locally.
- **INVITE POPUP SPAM FIXED** ("~50 invites on fresh browser, must spam Decline"): root cause — on a fresh browser the seen-message store (`chatx_seen_msg_ids`) is empty, so the 5s invite poll walked EVERY historical invite message and popped one modal per message. **Fix** in `templates/invite_poll.html` + `templates/dashboard/chatx.html`: recency filter (only pop invites sent in the last 15 min, using `m.timestamp`), one-popup-at-a-time queue (pending list + lock, next shows after close/decline/auto-dismiss), old invites silently marked seen. **Verified via Playwright**: 90-min-old invite skipped, fresh invite shows exactly one popup, zero JS errors.
- **render.yaml rewritten to current Blueprint spec** (the old one had deprecated `redis:` top-level key, legacy `plan: basic` DB name, and no KV `ipAllowList`): Redis is now a `type: keyvalue` service with `ipAllowList: []` (web connects over private network — always allowed, zero public exposure), DB uses current `basic-256mb` plan, `REDIS_URL` fromService references `type: keyvalue`, AI keys (GROQ/GEMINI/OPENROUTER) use `sync: false` so Render prompts but the app works without them, `preDeployCommand` now also runs idempotent `seed_shop` + `seed_achievements` so a fresh DB has shop/achievements/titles.
- **Secrets hygiene**: `.env` confirmed gitignored and untracked (only `.env.example` is tracked); grep across the repo found no committed API keys. `.env.example` updated to note AI keys are OPTIONAL.
- **.gitignore**: added `.opencode/`, `.playwright-mcp/`, `graphify-out/`, `docs/` (duplicate of root README), `staticfiles/`, stray screenshots. Root README.md restored (was deleted in working tree).

## Next Steps
- Test full invite-accept-play flow end-to-end
- Test progress sync in all 9 game types
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
