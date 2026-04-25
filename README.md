# Echo_Nest

Echo_Nest is a Flask-based wellness tracker and AI-supported reflection app. It combines mood logging, behavior context, emotional-state mapping, journaling insights, recovery suggestions, and lightweight forecasting inside one gentle, story-driven dashboard.

Instead of acting like a plain mood diary, Echo_Nest tries to behave more like a supportive wellness companion: it watches for patterns in sleep, mood, routines, and notes, then responds with context-aware guidance, micro-activities, journaling prompts, music recommendations, and habit-based encouragement.

## What It Is

Echo_Nest helps a user:

- log mood with sleep, screen time, activities, interaction level, and reflective notes
- classify emotional states like `calm`, `focus`, `peace`, `sad`, `angry`, and `gloomy`
- view emotional trends and dominant states on a readable dashboard
- receive context-aware companion responses based on recent behavior and mood patterns
- get CBT-style reframes for negative thought patterns
- see journaling insights and recurring concerns
- use adaptive reset activities matched to emotional state
- build recovery habits with streaks, weekly goals, and badges
- get music recommendations through Spotify and YouTube
- forecast the next likely mood signal from recent history

## Why It Feels Different

Many mood trackers stop at recording how a person feels. Echo_Nest is designed to go further.

What makes it different:

- It tracks context, not just mood scores.
  Sleep, activities, screen time, social interaction, and notes all shape the interpretation.

- It translates mood into emotional states.
  Instead of only saying "3 out of 5," it identifies states like `focus`, `peace`, `sad`, or `gloomy`.

- It responds to rough patches.
  Poor sleep, emotional dips, streak drops, sadness, anger, and foggy periods can trigger more supportive companion responses.

- It offers next steps, not just analysis.
  Users get adaptive resets, journaling prompts, and supportive nudges instead of a static chart alone.

- It includes behavior-based encouragement.
  Recovery habits, streaks, weekly goals, and badges are built into the experience.

- It supports real integrations with graceful fallback.
  OpenAI, Spotify, and YouTube can be used when configured, but the app still works locally without them.

## How It Works

### 1. Log With Context
The user submits:

- mood from `1` to `5`
- sleep hours
- interaction level
- screen time hours
- activities
- notes

### 2. Classify Emotional State
Echo_Nest uses the logged data plus note sentiment to classify the entry into a richer state such as:

- `calm`
- `energy`
- `happiness`
- `focus`
- `peace`
- `sad`
- `angry`
- `gloomy`

This logic now lives primarily in [app/services/emotion.py](/e:/echo_nest/app/services/emotion.py:1), with routing in [app/mood.py](/e:/echo_nest/app/mood.py:1).

### 3. Build the Dashboard Story
The dashboard summarizes:

- average mood
- dominant state
- sleep and interaction averages
- trend direction
- top activities
- real-time suggestions
- adaptive reset activity
- weekly reflection wins and watchouts
- per-entry "why this state?" explanations

### 4. Generate Companion Support
The companion layer reviews:

- recent mood history
- recent sleep averages
- logging streaks
- reset streaks
- latest notes
- emotional-state patterns

It then produces:

- supportive response text
- flags such as `poor_sleep`, `streak_drop`, or `needs_debrief`
- CBT-style reframe
- session debrief prompt
- journaling insight
- music recommendations
- gamification snapshot

This logic lives in [app/companion.py](/e:/echo_nest/app/companion.py:1).

### 5. Use Live Integrations When Available
If keys are configured:

- OpenAI can generate journal analysis
- Spotify can return live playlist matches
- YouTube can return live search results

If keys are missing or unavailable, Echo_Nest falls back to:

- local heuristic journaling analysis
- smart Spotify/YouTube search links

This logic lives in [app/integrations.py](/e:/echo_nest/app/integrations.py:1).

## Core Features

### Mood Logging
- daily entry form with structured context
- notes-based sentiment cues
- emotional-state classification
- edit and delete support for existing entries
- friendlier validation with clearer form errors

### Dashboard
- trend chart
- dominant emotional states
- behavior signals
- top anchors
- adaptive reset module
- forecast view
- weekly reflection summary
- entry explainability cards
- historical analytics for weekday patterns, recovery spikes, and monthly drift

### AI Wellness Companion
- context-aware responses
- poor-sleep and state-drop detection
- empathetic support language
- CBT-style thought reframes
- debrief prompts after difficult states

### AI Journaling
- recurring-concern analysis
- repeated-theme extraction
- emotional insight summary
- follow-up reflection prompt
- optional OpenAI-backed analysis

### Music Support
- state-aware Spotify recommendations
- state-aware YouTube recommendations
- fallback search links when API keys are absent

### Gamification
- reset completions
- streak tracking
- weekly goals
- total points
- achievement badges

## Landing Page Direction

The landing page is intentionally different from the dashboard.

It now focuses on:

- what the companion actually does
- why it is more than a mood tracker
- what happens after a rough day
- how the product moves from logging to understanding to response

Only the landing page was redesigned; the rest of the app remains structurally unchanged.

## Project Structure

- [app/mood.py](/e:/echo_nest/app/mood.py:1): routes and API endpoints
- [app/services/emotion.py](/e:/echo_nest/app/services/emotion.py:1): emotion-state rules and explainability
- [app/services/dashboard.py](/e:/echo_nest/app/services/dashboard.py:1): dashboard summaries and weekly reflection
- [app/services/validation.py](/e:/echo_nest/app/services/validation.py:1): form validation
- [app/services/companion_support.py](/e:/echo_nest/app/services/companion_support.py:1): companion analysis helpers
- [app/services/gamification.py](/e:/echo_nest/app/services/gamification.py:1): streaks, badges, and points
- [app/content.py](/e:/echo_nest/app/content.py:1): JSON-backed content/config loading
- [app/env.py](/e:/echo_nest/app/env.py:1): lightweight `.env` autoloading
- [app/schemas.py](/e:/echo_nest/app/schemas.py:1): API response schemas
- [app/companion.py](/e:/echo_nest/app/companion.py:1): companion reasoning, journaling fallback, gamification
- [app/integrations.py](/e:/echo_nest/app/integrations.py:1): OpenAI, Spotify, YouTube integration helpers
- [app/data/emotion_config.json](/e:/echo_nest/app/data/emotion_config.json:1): emotion rules/content
- [app/data/companion_config.json](/e:/echo_nest/app/data/companion_config.json:1): companion copy/content
- [app/models.py](/e:/echo_nest/app/models.py:1): SQLModel models
- [app/database.py](/e:/echo_nest/app/database.py:1): engine setup, SQLite schema backfill helpers
- [app/ml.py](/e:/echo_nest/app/ml.py:1): mood forecast model loading and prediction
- [app/utils.py](/e:/echo_nest/app/utils.py:1): palette and generated CSS helpers
- [app/templates/index.html](/e:/echo_nest/app/templates/index.html:1): landing page
- [app/templates/dashboard.html](/e:/echo_nest/app/templates/dashboard.html:1): dashboard UI
- [app/templates/base.html](/e:/echo_nest/app/templates/base.html:1): shared shell and home-page styling
- [run.py](/e:/echo_nest/run.py:1): app entrypoint
- [test/test_api.py](/e:/echo_nest/test/test_api.py:1): smoke and route tests

## Color Palette

The main palette lives in [app/utils.py](/e:/echo_nest/app/utils.py:1).

### Brand / UI Colors

- `primary`: `#FFB7A5`
- `accent`: `#7EDFC0`
- `bg_light`: `#FDF7F1`
- `bg_dark`: `#15202B`
- `text_dark`: `#212529`
- `text_light`: `#E5E7EB`
- `ink_soft`: `#5F5A56`
- `line_soft`: `#E7DDD5`

### Emotional State Colors

- `calm`: `#A8D5BA`
- `energy`: `#F8C784`
- `happy`: `#FFF9A6`
- `focus`: `#D4B4E2`
- `peace`: `#C9E4FF`
- `sad`: `#8FA6BF`
- `angry`: `#E98282`
- `gloomy`: `#6B7280`

### RGB Variables Used For Effects
Defined in [app/templates/base.html](/e:/echo_nest/app/templates/base.html:1):

- `255, 183, 165`
- `126, 223, 192`
- `168, 213, 186`
- `248, 199, 132`
- `255, 249, 166`
- `212, 180, 226`
- `201, 228, 255`
- `143, 166, 191`
- `233, 130, 130`
- `107, 114, 128`

## Run The App

Install dependencies first if needed:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

From the project root:

```powershell
.\start_server.ps1
```

Then open:

```text
http://127.0.0.1:5000
```

If you prefer running Python directly:

```powershell
.\.venv\Scripts\python.exe run.py
```

For background server management:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_server_detached.ps1
powershell -ExecutionPolicy Bypass -File .\server_status.ps1
powershell -ExecutionPolicy Bypass -File .\stop_server.ps1
```

If `python run.py` behaves unreliably in your shell session, this foreground command is the most reliable fallback:

```powershell
python -c "from app import create_app; app=create_app(); app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)"
```

Keep that terminal open while the server is running.

## Environment Variables

Copy values from [.env.example](/e:/echo_nest/.env.example:1) if you want live provider integrations.

### Core

```env
SECRET_KEY=change-me
DATABASE_URL=sqlite:///echo_nest.db
HOST=127.0.0.1
PORT=5000
LOG_LEVEL=INFO
```

### OpenAI Journaling

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

### Spotify

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

### YouTube

```env
YOUTUBE_API_KEY=
```

## Integration Behavior

- If `OPENAI_API_KEY` is present, journal analysis can use the OpenAI API.
- If Spotify credentials are present, playlist recommendations can use live Spotify search.
- If `YOUTUBE_API_KEY` is present, YouTube recommendations can use live search results.
- If keys are missing or calls fail, Echo_Nest falls back gracefully.

Fallback behavior:

- journaling uses local heuristic analysis
- Spotify uses search links
- YouTube uses search links

## Data Model Overview

### `User`
- email
- password hash
- related mood entries
- related habit events

### `Entry`
- date
- mood
- emotion state
- activities
- sleep hours
- interaction level
- screen time
- notes
- timestamp

### `HabitEvent`
- occurred date
- habit key
- habit title
- emotional state
- points
- timestamp

See [app/models.py](/e:/echo_nest/app/models.py:1).

## Main Routes

### Pages
- `/`: landing page
- `/auth/register`: register
- `/auth/login`: login
- `/log`: create mood entry
- `/entries/<id>/edit`: edit an existing entry
- `/dashboard`: main wellness dashboard

### APIs
- `/api/predict`: forecast next mood
- `/api/capture`: emotion capture endpoint
- `/api/companion/chat`: companion response endpoint
- `/api/habit/complete`: save habit completion and refresh rewards

API responses are shaped through typed dataclass schemas in [app/schemas.py](/e:/echo_nest/app/schemas.py:1).

## Verification

These checks passed locally:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

I also verified:

- register/login flow
- mood logging
- validation error handling
- landing page rendering
- dashboard rendering
- edit/delete entry flow
- `.env` loading behavior
- historical analytics summary generation
- `/api/predict`
- `/api/companion/chat`
- `/api/habit/complete`

The app was also smoke-tested through Flask's test client for:

- context-aware companion output
- weekly-goal updates
- live-provider fallback behavior

## Notes

- The app uses SQLite by default.
- The local test environment may still be missing some `pytest` dependencies, so compile checks and Flask test-client smoke tests were used for validation.
- OpenAI, Spotify, and YouTube support are optional enhancements, not hard requirements.
- The current journaling system is hybrid:
  live LLM analysis when configured, local rules when not.
- The music system is also hybrid:
  live provider results when configured, smart links when not.

## Future Improvements

- add friendlier setup instructions for API keys
- add image-based emotion capture guidance to the README
