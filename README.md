# MovieStream

A Netflix-style movie streaming platform built with Flask.

## Milestone 3 — Admin Panel (current)

A real admin role with real enforcement, not just a hidden page.

- **Default admin account** seeded automatically on first run when the users table is empty. Set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`; without `ADMIN_PASSWORD` the `admin@moviestream.com` / `admin123` fallback is only used in development (`DEBUG`), never in production. Promote any other user to admin with `flask --app app create-admin someone@example.com`.
- **Production requires `SECRET_KEY`**: with `FLASK_ENV=production` the app refuses to start if it isn't set.
- **CSRF**: every state-changing request (forms *and* the JSON API) needs a CSRF token. `api.js` sends it automatically as `X-CSRFToken`; programmatic API clients must do the same.

## Running tests

```bash
python -m unittest discover tests
```
- **`is_admin` and `is_active` columns** on `User`. Every `/admin/*` route is protected by an `@admin_required` decorator: not-logged-in visitors are redirected to login, logged-in non-admins get a real 403 page.
- **Dashboard** (`/admin`): live counts (movies, users, genres, languages, favorites), real disk-space usage (walks `static/movies` + `static/posters`, not just a database guess), most-favorited movies, recent movies/users.
- **Movie management** (`/admin/movies`): edit any movie's metadata, optionally replace its video/poster/trailer (old file is deleted once the new one is confirmed saved); delete a movie (removes its DB row *and* its files on disk).
- **Category management** (`/admin/categories`): add genres; delete is blocked with a clear message if any movie still uses that genre, instead of silently breaking those movies' data.
- **User management** (`/admin/users`): promote/demote admin status, activate/deactivate accounts. A deactivated account is genuinely blocked from logging in (distinct "this account has been disabled" message, not a generic wrong-password error). An admin can't demote or deactivate themselves, so it's not possible to accidentally lock yourself out.

**Not in this milestone** (still pending): password reset/email verification, comments/ratings, subtitles/multi-audio, JWT API auth, Docker/CI-CD, automated tests, account-linked Continue Watching, Series support.

## Milestone 2 — User System

Real accounts, real sessions, real server-side data — not a mock login screen.

- **Register / Login / Logout**: `/register`, `/login`, `/logout`. Passwords are hashed with bcrypt (never stored in plain text). Logout is a CSRF-protected POST (not a bare link) so it can't be triggered by a stray request.
- **Sessions**: Flask-Login manages the session cookie; "Remember me" on login extends it to 7 days (`PERMANENT_SESSION_LIFETIME`).
- **Profile**: `/profile` shows your username, bio, join date, and favorited movies. `/profile/edit` lets you change username/email/bio and upload a real profile photo, with a live preview before you submit.
- **Server-side Favorites**: replaces the localStorage-only "My List" from Milestone 1 *for logged-in users*. Favoriting a movie now writes to a `favorites` table tied to your account — `GET/POST /api/favorites`, `DELETE /api/favorites/<id>`.
- **Guest fallback preserved**: if you're not logged in, My List still works exactly as it did in Milestone 1 (localStorage). Log in or register and your guest list is automatically migrated onto your new account via `POST /api/favorites/sync` — nothing gets lost.
- **Auth-aware everywhere**: navbar swaps Login/Sign Up for a profile dropdown (Profile / Edit Profile / Logout) once you're logged in; `/api/*` routes return a JSON 401 instead of an HTML redirect when hit by JS while logged out.

**Not in this milestone** (arriving later): password reset / email verification, admin panel & role-based access, comments/ratings tied to accounts, JWT-based API auth, Watch History / Continue Watching tied to an account (the player's auto-resume still works locally via `localStorage`, same as Milestone 1).

## Milestone 1 — Fully Functional Local Streaming Platform

Everything listed below is genuinely wired end-to-end — no placeholder buttons. Every file referenced (video, trailer, poster) is a real, playable file shipped in this project (short original demo clips generated for testing, not copyrighted film content).

**Catalog & Home Page**
- Dynamic hero banner driven by the featured/top-rated movie in SQLite (poster, title, meta, description all real data)
- Horizontally scrolling rows: Trending, Top Rated, Recently Added, one row per genre
- Movie cards pull poster, rating, year, runtime, and language straight from the database
- Drag-to-scroll / mouse-wheel / keyboard horizontal scrolling

**Functional Search**
- Live-typing suggestions dropdown in the navbar (debounced, keyboard navigable)
- Full `/search` results page with filters: genre, language, year, min rating
- Backed by a real `GET /api/movies/search` and `GET /api/movies` endpoint (not client-side mock data)

**Functional Play & Trailer**
- Play buttons (hero, cards, detail page) navigate to `/movie/<id>` and autoplay a real `<video>` element
- Custom player: play/pause, 10s skip back/forward, seek bar, volume + mute, playback speed, fullscreen, Picture-in-Picture, keyboard shortcuts (space/arrows/M/F), double-click-to-fullscreen
- Auto-resume: playback position is saved to `localStorage` and restored on return
- Auto-continue: an "Up Next" prompt appears when a movie ends, linking to a similar title
- Trailer button opens a modal and plays a genuinely separate, shorter trailer file

**Functional My List** (now server-side for logged-in users — see Milestone 2 above)
- Heart/plus icon on every card, hero, and detail page toggles a real watchlist
- `/my-list` renders server-side for logged-in users; guests still get the localStorage version
- "Watch Later" is wired the same way with its own separate list


**Upload System**
- `/upload` page: real multipart form (title, description, genre, language, year, runtime, rating, poster, trailer, video) with a live byte-accurate progress bar
- Duplicate detection: every uploaded video is SHA-256 hashed; re-uploading the same file is rejected with a 409 and a link to the existing movie
- Automatic metadata detection: if runtime is left blank, it's read from the real video file via `ffprobe`; if no poster is uploaded, one is auto-extracted from a video frame via `ffmpeg` — both gracefully skipped (falling back to the CSS placeholder card, never a fake image) if ffmpeg isn't installed
- "Scan Library Folder" button: automatic movie detection for files dropped directly into `static/movies/` without going through the form — titles are guessed from the filename, posters/durations are auto-detected the same way

**REST API** (`/api/*`)
- `GET /api/movies` — list with `q`, `genre`, `language`, `year`, `min_rating`, `ids`, `sort`, `page`, `per_page`
- `GET /api/movies/search` — lightweight version for the live dropdown
- `GET /api/movies/<id>` — single movie
- `POST /api/movies/upload` — multipart upload (same pipeline the `/upload` page uses)
- `PATCH /api/movies/<id>` — partial update
- `DELETE /api/movies/<id>` — deletes the row and its files on disk
- `POST /api/movies/scan` — automatic library detection
- `GET /api/genres`, `GET /api/languages`

**Also included:** custom 404/500 pages, offline page + service worker, fully responsive layout, dark/cyan Netflix-inspired theme throughout.

**Not in this milestone** (arriving in the User System milestone, so each feature ships with the models/routes/forms it actually needs): user accounts & login, server-side favorites/watch history tied to an account, admin panel/dashboard, comments/ratings from users, subtitles/multi-audio/quality selector, Docker/CI-CD, automated test suite.

## Project Structure

```
MovieStream/
├── app.py                      # Application factory + entry point (Flask-Login, Bcrypt wired here)
├── config.py                   # Dev / Production config classes
├── database.py                 # SQLAlchemy instance, init_db(), seed_db()
├── models.py                   # Movie, Genre, Language, User, Favorite models
├── forms.py                    # MovieUploadForm, Registration/Login/Profile/Logout forms
├── media.py                    # Shared upload/hash/ffprobe/ffmpeg helpers
├── requirements.txt
├── .env.example
├── .gitignore
├── blueprints/
│   ├── main/                   # Home page, search results, My List page
│   │   ├── routes.py
│   │   └── services.py
│   ├── movies/                 # Movie detail/watch page, upload page
│   │   ├── routes.py
│   │   └── services.py         # Upload pipeline + automatic library scan
│   ├── api/                    # JSON REST API under /api
│   │   ├── routes.py           # Movies CRUD/search + Favorites CRUD/sync
│   │   └── services.py         # Search/filter/sort/paginate query builder
│   ├── auth/                   # Register, login, logout, profile
│   │   ├── routes.py
│   │   └── services.py         # Registration/auth/profile-update logic
│   └── admin/                  # Dashboard, movie/category/user management
│       ├── routes.py           # Every route protected by @admin_required
│       └── services.py         # Stats, storage usage, category/user actions
├── templates/
│   ├── base.html
│   ├── partials/
│   │   ├── navbar.html         # Search form, nav links, My List
│   │   ├── footer.html
│   │   └── macros.html         # movie_card / movie_row Jinja macros
│   ├── main/
│   │   ├── home.html
│   │   ├── search_results.html
│   │   └── my_list.html
│   ├── movies/
│   │   ├── detail.html         # Player + metadata + similar movies
│   │   └── upload.html
│   ├── auth/
│   │   ├── register.html
│   │   ├── login.html
│   │   ├── profile.html
│   │   └── edit_profile.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
├── static/
│   ├── css/
│   │   ├── variables.css       # Design tokens
│   │   ├── base.css
│   │   ├── navbar.css          # Now includes the logged-in user dropdown
│   │   ├── hero.css
│   │   ├── movie-card.css
│   │   ├── home.css
│   │   ├── player.css
│   │   ├── upload.css
│   │   ├── auth.css            # Login/register/profile pages
│   │   └── components.css      # Toasts, trailer modal, search dropdown
│   ├── js/
│   │   ├── api.js              # fetch() wrapper for every /api/* call, incl. Favorites
│   │   ├── main.js             # Toasts, My List (server Favorites or localStorage), trailer modal
│   │   ├── navbar.js           # Scroll effect + mobile menu
│   │   ├── horizontal-scroll.js
│   │   ├── movie-card.js       # Play/My List/Watch Later/Share on every card
│   │   ├── hero.js             # Hero banner button wiring
│   │   ├── search.js           # Live search dropdown
│   │   ├── player.js           # Custom video player controls
│   │   ├── upload.js           # Progress bar + library scan button
│   │   ├── my-list.js          # Guest (localStorage) rendering for /my-list
│   │   ├── auth.js             # Live avatar preview on /profile/edit
│   │   └── sw-register.js
│   ├── service-worker.js
│   ├── offline.html
│   ├── images/
│   ├── posters/                # 6 auto-generated demo posters ship here
│   ├── movies/                 # 6 demo movie clips + trailers ship here
│   └── avatars/                # User profile photos land here
├── uploads/                    # Staging area (currently unused; uploads save straight to static/)
└── instance/                   # SQLite database file lives here (gitignored)
```

## Setup

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **(Optional but recommended) install ffmpeg** for automatic poster/duration detection on upload:

   ```bash
   # Debian/Ubuntu
   sudo apt install ffmpeg
   # macOS
   brew install ffmpeg
   ```

   The app works without it — you'll just need to fill in runtime manually and upload your own poster image.

4. **Configure environment variables:**

   ```bash
   cp .env.example .env
   # then edit .env and set a real SECRET_KEY
   ```

5. **Run the app:**

   ```bash
   python app.py
   ```

   On first run this creates `instance/moviestream.db` and seeds it with 6 sample movies — each with a real, playable demo video, trailer, and poster already in `static/movies/` and `static/posters/`.

6. Open **http://127.0.0.1:5000** in your browser.

### Alternative: Flask CLI

```bash
export FLASK_ENV=development   # Windows: set FLASK_ENV=development
flask --app app run --debug
```

(Note: the CLI path does not auto-seed the database — run `python app.py` at least once first.)

## Database Migrations

```bash
flask --app app db init      # once, first time only
flask --app app db migrate -m "description of change"
flask --app app db upgrade
```

## Try It Out

- Click **Play** on any card or the hero banner — a real video plays with full custom controls
- Click **Trailer** — a separate, shorter clip plays in a modal
- Click the **+ (My List)** icon — then visit **My List** in the nav to see it there
- Type in the **search bar** — live suggestions appear; press Enter for the full results page with filters
- Go to **Upload** — submit a video file (mp4/webm/mov/mkv) and watch the real progress bar; try uploading the same file twice to see duplicate detection in action
- On the Upload page, click **Scan Library Folder** after manually dropping a video file into `static/movies/` to see automatic detection register it
- Click **Sign Up**, create an account, then favorite a few movies as a guest *before* logging in — after you register/log in, your guest list is automatically migrated onto your account
- Visit **Profile** to see your favorites, or **Edit Profile** to change your username/bio/photo (with a live preview before saving)
- Log out and back in — your favorites are still there, now truly server-side
