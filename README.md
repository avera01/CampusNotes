# CampusNotes

A regional study resource repository for university students — starting with
Nagaland University and its affiliated colleges. Students browse and upload
notes, previous year question papers, and syllabus documents organized by
University → Course → Semester → Subject.

## Tech stack

- **Backend:** Flask (Python), Flask-SQLAlchemy, Flask-Login (session auth), Flask-WTF, Authlib ("Sign in with Google")
- **Database:** SQLite for local dev (swap to PostgreSQL later via one env var)
- **Frontend:** Jinja templates, plain CSS, a little vanilla JS for cascading dropdowns
- **File storage:** local disk under `app/uploads/` (swap to S3/Cloudinary later by
  editing `app/resources/storage.py` only — routes and templates don't change)

## Project structure

```
campusnotes/
├── app/
│   ├── __init__.py          # app factory
│   ├── config.py            # env-driven config
│   ├── extensions.py        # db, migrate, login_manager instances
│   ├── models.py            # University, Course, Semester, Subject, User, Resource
│   ├── auth/                # signup, login, logout
│   ├── main/                # home, browse/search, cascading-dropdown JSON API
│   ├── resources/           # upload, detail, download, PDF preview, storage.py
│   ├── admin/                # verify/unverify queue
│   ├── templates/
│   ├── static/               # css/style.css, js/cascade.js
│   └── uploads/              # uploaded files (gitignored)
├── migrations/                # Flask-Migrate versions (created by `flask db init`)
├── seed.py                    # sample data: Nagaland University, 10 courses, subjects, test users
├── run.py                     # entrypoint
├── requirements.txt
└── .env.example
```

## Database schema

```
University (1) ──< Course (1) ──< Semester (1) ──< Subject (1) ──< Resource
                                                                        │
User ───────────────────────────────────────────< uploads ────────────┘
```

- **University** — `name`, `code` (unique)
- **Course** — belongs to a University; e.g. "BCA"
- **Semester** — belongs to a Course; `number` 1–6, unique per course
- **Subject** — belongs to a Semester; e.g. "Data Structures", unique per semester
- **Resource** — belongs to a Subject and a `uploader` (User); has `resource_type`
  (`notes` / `pyq` / `syllabus`), `is_verified`, `is_premium`, `download_count`,
  and file metadata (`file_path`, `file_type`, `file_size`)
- **User** — `email`, `password_hash` (nullable — Google-only accounts have
  none), `role` (`student` / `admin`), `auth_provider` (`email` / `google`,
  set once at creation, informational only), `google_sub` (Google's stable
  per-account ID, if they've ever signed in with Google); optionally linked
  to a University/Course + `current_semester` for profile display only

`is_premium` is a boolean flag only — locked resources show a "Premium" badge
and block preview/download for everyone except the uploader and admins. There's
no payment integration yet; that's future work.

## Setup

### 1. Prerequisites

- Python 3.11+ (check with `python --version`)

### 2. Create a virtual environment and install dependencies

```bash
cd campusnotes
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Generate a real `SECRET_KEY` and put it in `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The defaults for `DATABASE_URL` (SQLite) and `UPLOAD_FOLDER` work as-is for
local dev.

#### Setting up "Sign in with Google" (optional)

The rest of the app works fine without this — email/password auth is
unaffected — but if you want the Google button to actually work:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and
   create a project (or pick an existing one).
2. **APIs & Services → OAuth consent screen** — set it up for "External"
   users (unless you have a Google Workspace org and want "Internal"), fill
   in the required app name/support email, and add your own Google account
   as a test user while the app is in "Testing" mode.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   — choose **Web application**, and add:
   - **Authorized JavaScript origin:** `http://127.0.0.1:5000`
   - **Authorized redirect URI:** `http://127.0.0.1:5000/auth/google/callback`

   (`http://127.0.0.1`/`localhost` is allowed by Google for local dev only.
   When you deploy somewhere, add that deployment's `https://` callback URL
   too, e.g. `https://yourapp.onrender.com/auth/google/callback`.)
4. Copy the generated **Client ID** and **Client Secret** into `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

### 4. Initialize the database and load sample data

```bash
python seed.py
```

This creates all tables (via SQLAlchemy, no migration step needed for a fresh
DB) and inserts:

- Nagaland University
- 10 courses: BA, BBA, BCA, BCom, BSc (6 semesters each) and MA, MBA, MCA, MCom, MSc (4 semesters each)
- Sample subjects per semester (Data Structures, DBMS, C++ Programming, etc.)
- Two test accounts:
  - **Admin:** `admin@campusnotes.edu` / `admin123`
  - **Student:** `student@campusnotes.edu` / `student123`

Change these passwords before deploying anywhere beyond your own machine.

Re-running `python seed.py` is safe — it skips rows that already exist.

### 5. Run the app

```bash
python run.py
```

Visit `http://127.0.0.1:5000`.

### 6. Try it out

1. Log in as the student account (or sign up your own).
2. From **Account**, go to **Upload a resource**, pick University → Course →
   Semester → Subject, attach a PDF/DOCX/image, and submit.
3. Go to **Home** or **Search**, filter/search for it, open it, download it.
4. Log in as the admin account, go to **Admin**, and mark the resource as
   **Verified** — the "Verified" badge appears on Home/Search and the detail page.
5. Try uploading a resource with **Mark as Premium** checked, then view it
   while logged out — it should show as locked instead of downloadable.
6. From **Account → Settings**, try switching the theme (Light/Dark/Match
   system), updating your profile, and changing your password.
7. If you've set up Google credentials, try **Continue with Google** on the
   login or signup page. Signing in with a Google account whose email
   matches an existing account logs into that same account (linking by
   email) instead of creating a duplicate.

## Schema migrations (for future changes)

The app ships with Flask-Migrate configured. After changing `app/models.py`:

```bash
flask --app run.py db init      # first time only
flask --app run.py db migrate -m "describe the change"
flask --app run.py db upgrade
```

## Moving beyond local dev

- **Database:** set `DATABASE_URL` to a `postgresql://...` URI — no code
  changes needed, since all queries go through SQLAlchemy.
- **File storage:** reimplement `save_resource_file()` /
  `resource_file_location()` in `app/resources/storage.py` to talk to
  S3/Cloudinary instead of the local disk; routes and templates are unaffected.
- **Deployment:** the app is a standard Flask app (`run.py` exposes `app`),
  so it deploys to Render/Railway/PythonAnywhere the same way any Flask app
  does — set `SECRET_KEY`, `DATABASE_URL`, and a writable `UPLOAD_FOLDER` (or
  swap to cloud storage first, since most of these platforms don't persist
  local disk across deploys).

## Scope notes

This is the MVP as specified: user auth + profiles, the browsable content
hierarchy, upload, browse/search/sort, download/preview, admin verification,
and a premium-flag scaffold with no payment integration. No chat, no social
feed, no other features beyond this were added.
