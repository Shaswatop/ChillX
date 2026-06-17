# ChillX — Multiplayer Arena

Real-time multiplayer gaming platform with 9 games, voice/video calls, chat, challenges, and social features.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Shaswatop/ChillX.git
cd ChillX

# 2. Backend
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# 3. Frontend (for React/JSX compilation)
npm install
```

Open http://localhost:8000

## Games

- Typing (Monkeytype-style, multiplayer with live opponent cursor)
- Quiz (AI-generated, 10+ categories, multiplayer)
- Runner (platformer, mobile controls included)
- Aim Trainer 3D
- CPS (Click Per Second)
- Reaction Time
- Memory Card
- Tic Tac Toe
- Fitness Workout Tracker

## Play with Friends Online

```bash
python manage.py runserver 0.0.0.0:8000
cloudflared tunnel --url http://localhost:8000
```

Share the `https://*.trycloudflare.com` URL with friends.

## Tech Stack

- **Backend:** Django 6, Django Channels (WebSockets), SQLite
- **Frontend:** React (Babel standalone), vanilla JS
- **Real-time:** WebSockets for multiplayer sync, HTTP polling for chat/calls
- **Auth:** JWT (SimpleJWT)
- **Voice/Video:** WebRTC with HTTP signaling
