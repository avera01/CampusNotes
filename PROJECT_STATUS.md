# CampusNotes — Project Status

_Last updated: 2026-07-22. Written as a handoff/context snapshot — if you're
picking this up fresh, read this before diving into the code._

Repo: https://github.com/avera01/CampusNotes (branch `main`, latest commit
`5549abc`). Deployed on Render (free tier — no Shell access, ephemeral
filesystem). Local dev uses SQLite; production uses Render Postgres.

## What's built

**Core MVP** (per the original spec):
- University → Course → Semester → Subject → Resource content hierarchy
- Email/password auth (session-based via Flask-Login, not JWT — see Decisions)
- Resource upload (PDF/DOCX/image) tagged to a Subject, with download counter
- Home (`/`, filter-only: University/Course/Semester/Sort) and Search
  (`/search`, same filters + keyword search) as separate pages
- PDF inline preview (iframe) + download; premium-flag lock (UI/logic only,
  no payment integration)
- Admin resource verification (verify/unverify, "Verified" badge)
- Seed script (`seed.py`) — Nagaland University, 10 courses (BA/BBA/BCA/BCom/
  BSc at 6 semesters, MA/MBA/MCA/MCom/MSc at 4), sample subjects, 2 test
  accounts (`admin@campusnotes.edu` / `student@campusnotes.edu`, both
  `password: <role>123`)

**Added beyond the original spec** (all user-requested):
- Light/Dark theme toggle (instant, client-side, cookie-based — not tied to
  a user account)
- Settings page: edit profile, change password, theme toggle
- Profile picture upload with client-side cropping (Cropper.js) — crop/zoom/
  reposition with a live circular preview, uploaded as a blob via fetch,
  server-side reprocessed with Pillow (EXIF-rotation-fixed, resized to
  300×300, saved as JPEG, fixed filename per user so re-uploads overwrite)
- Circular nav avatar (uploaded photo or an initials fallback), gear-icon
  Settings link
- "Sign in with Google" (Authlib/OIDC) — see Google OAuth section below
- Show/hide password eye-icon toggle on all password fields (shared Jinja
  macro + one JS file)
- Subject and Semester are now free text on the upload form (was
  University/Course/Semester/Subject all dropdowns; Subject went through a
  brief free-text + datalist stage before landing on plain free text;
  Semester was converted last, see "In progress"). University and Course
  are still dropdowns (still cascading via JS, University → Course), since
  the app has no natural free-text identifier for those.
- About Us page
- Admin catalog management UI (`/admin/catalog`) — create-only forms for
  University/Course/Semester/Subject, since Render's free tier has no Shell
  to run `seed.py`-style scripts by hand

**Deployment readiness work:**
- `requirements.txt` is a full pinned lockfile (`pip freeze` output, not
  just top-level deps) — includes `gunicorn` and `psycopg2-binary`
- `DATABASE_URL` / `SECRET_KEY` confirmed read from env vars; `postgres://`
  URLs auto-normalized to `postgresql://` (some hosts still hand out the
  old scheme, which modern SQLAlchemy rejects)
- `db.create_all()` runs automatically on every app startup (idempotent,
  wrapped in try/except) — no Shell access to run migrations by hand
- `INITIAL_ADMIN_EMAIL` env var promotes a matching user to admin on every
  startup, same no-Shell-access rationale (see Decisions)

## In progress / incomplete

1. **Google OAuth on production is currently broken**
   (`Error 400: redirect_uri_mismatch`). Two things need fixing, neither
   done yet:
   - The Google Cloud Console OAuth client only has the **local dev**
     redirect URI registered (`http://127.0.0.1:5000/auth/google/callback`).
     The production callback URL (Render's `https://<app>.onrender.com/auth/
     google/callback`) was never added — need the exact Render URL from the
     user to register it.
   - **`ProxyFix` is not configured** (confirmed absent from the codebase
     as of this writing). Render terminates HTTPS at a proxy and forwards
     to the app over plain HTTP; without `ProxyFix` reading the
     `X-Forwarded-Proto` header, Flask's `url_for(..., _external=True)`
     (used to build the OAuth redirect_uri) likely generates `http://`
     URLs even on the live HTTPS site — which would cause this exact
     mismatch even after the Google Console URI is fixed. This was mid-fix
     when interrupted by a higher-priority request; the fix itself
     (adding `werkzeug.middleware.proxy_fix.ProxyFix` in the app factory)
     was never applied.

2. **Subject field history**: went through three iterations this session —
   (a) originally a `<select>` dropdown populated via cascading JS, (b)
   changed to free text with `<datalist>` autocomplete suggestions pulled
   from existing subjects in the chosen semester, (c) per a follow-up
   request, the datalist suggestions were removed entirely — it's now a
   plain text input with no autocomplete. Backend logic (case-insensitive
   lookup-or-create against the chosen semester) has been stable since (b)
   and wasn't affected by the datalist removal in (c). This is **done**,
   not actually pending — flagging here only because it changed shape
   multiple times and is easy to misremember.

3. **Semester field converted to free text — done.** The upload form's
   cascade used to be University → Course → Semester (dropdown) → Subject
   (free text), with `semester_id` submitted directly from the JS-populated
   dropdown. Semester is now a plain number input (`semester_number`,
   `IntegerField`, 1–20) instead, and the JS cascade only goes
   University → Course. Since the server now needs to know which *course*
   a typed-in semester number belongs to, `course_id` became a real
   submitted `SelectField` (`validate_choice=False`, same pattern the old
   `semester_id` used) instead of the JS-only, never-submitted select it
   was before. The route (`app/resources/routes.py:upload`) does a
   `Semester.query.filter_by(course_id=..., number=...)`
   lookup-or-create, mirroring the existing Subject lookup-or-create —
   relies on the `uq_semester_course_number` unique constraint already on
   the `Semester` model. Verified end-to-end in the browser: submitting
   semester "7" under BCA created a new `Semester(course_id=1, number=7)`
   row; a second upload with the same course + "7" reused that same row
   (confirmed via direct DB query, no duplicate). Home/Search page filters
   are untouched — they still use the `Semester` dropdown fed by
   `/api/semesters`, since those are filtering existing data rather than
   creating new rows.

## Known pending issues / rough edges

- **PDF preview fix not fully visually verified.** The black-box preview
  bug was diagnosed as Chrome filling not-yet-painted iframe content with
  a dark background under `prefers-color-scheme: dark`, and fixed by
  forcing `color-scheme: light` on the preview iframe. This was confirmed
  applied correctly via computed styles, but the sandboxed browser tool
  used for verification can't render PDFs inline at all (even direct
  navigation to a PDF triggers a download dialog), so there's no confirmed
  visual proof the fix reaches Chrome's *internal* PDF viewer surface
  specifically. A fallback "Open in a new tab" link was added under the
  preview regardless, as a safety net independent of the root cause.
  **Ask the user to confirm** the black box is actually gone.
- **Google-only accounts and password change**: a user who signed up via
  Google (no `password_hash`) gets a generic "Current password is
  incorrect" error if they try the Settings → Change Password flow,
  instead of a proper "set a password" flow. Known, explicitly deferred
  (not in scope of the original Google OAuth request).
- **Render free tier has an ephemeral filesystem.** Uploaded resource
  files and profile pictures will be wiped on every redeploy/restart.
  Flagged to the user but not solved — `app/resources/storage.py` and
  `app/auth/avatar_storage.py` are structured so swapping to S3/Cloudinary
  later doesn't require route/template changes, but that swap hasn't been
  done.
- **No real migration history.** Flask-Migrate is installed and configured
  (`app/extensions.py`), but `flask db init` was never run — the
  `migrations/` folder is an empty placeholder. Every schema change so far
  has been handled by deleting the local dev DB and re-running `seed.py`
  (which calls `db.create_all()`), or, in production, by the automatic
  `db.create_all()` on startup. This works because `db.create_all()` only
  adds missing tables/columns-on-new-tables — it does **not** alter
  existing tables, so a genuine column-level migration on a live
  production DB with real data would currently require manual SQL (no
  tooling in place for that).
- **Admin catalog page is create-only** — no edit/delete for
  University/Course/Semester/Subject. Explicit scope boundary from the
  user's request, not a bug.
- Render free-tier Postgres external connections expire after 90 days
  (noted during the admin-promotion work, before the `INITIAL_ADMIN_EMAIL`
  env-var approach superseded the need for direct external DB access).

## Key decisions and why

- **Session auth (Flask-Login), not JWT.** The original spec asked for
  JWT, but this is a server-rendered Jinja app, not an SPA/API — sessions
  fit the architecture better. Explicitly confirmed with the user early on.
- **SQLite locally, Postgres in production**, abstracted entirely through
  `DATABASE_URL` — no code branches on database dialect.
- **Local disk storage for uploads**, deliberately structured (see
  `storage.py` files) to swap to S3/Cloudinary later without touching
  routes/templates — not yet done, see "Known pending issues."
- **Admin bootstrap via `INITIAL_ADMIN_EMAIL` env var**, not a one-off
  script or Shell command — chosen specifically because Render's free tier
  has no Shell access. Runs on every startup, idempotent (no-op once the
  user is already admin), only takes effect once the target account
  actually exists (i.e., after they've signed in at least once).
- **`db.create_all()` on every startup**, same no-Shell-access rationale.
  Wrapped in try/except to tolerate a narrow race if multiple gunicorn
  workers start concurrently and both attempt to create the same table.
- **Full pinned `requirements.txt`** (`pip freeze` style, ~30 packages)
  instead of a curated top-level-only list — chosen for deployment
  reproducibility once Render entered the picture, so it resolves the
  exact versions tested locally rather than whatever a resolver picks.
- **`postgres://` → `postgresql://` auto-normalization** in `config.py` —
  defensive fix for a well-known hosting-provider gotcha (modern
  SQLAlchemy rejects the old scheme outright).
- **`auth_provider` is informational only**, never used to gate login
  methods. Account linking is by email match (per explicit spec): if a
  Google sign-in matches an existing email/password account, it logs into
  that same account and leaves the password intact — both methods work
  afterward. `google_sub` is stored for reference but isn't the matching
  key.
- **Avatar storage uses a fixed filename per user**
  (`profile_pics/<user_id>.jpg`, always overwritten) — deliberately
  different from resource file storage (which renames on collision and
  keeps every file), because an avatar is inherently one-per-user.
- **Cache-busting via file mtime**, not manual version strings — both
  `versioned_static()` (JS/CSS) and `avatar_url()` (profile pictures)
  append `?v=<mtime>` automatically, so editing a file always invalidates
  browser caches with zero manual bookkeeping.
- **Theme is a cookie, not a DB column** — deliberately per-browser rather
  than per-account, so it works for logged-out users too and needed no
  schema change.
- **No PR workflow in practice** — one feature branch
  (`feature/bootstrap-admin-promotion`) was created and later merged
  directly into `main` (not via an actual GitHub PR) because the GitHub
  CLI isn't installed on this machine and no other GitHub API credentials
  were available. All other work has been committed straight to `main`.

## Environment variables in use

Read via `app/config.py`, loaded from `.env` locally (gitignored,
confirmed never committed) or Render's dashboard in production:

| Variable | Purpose | Required? |
|---|---|---|
| `SECRET_KEY` | Session/CSRF signing | Yes (falls back to an insecure dev default if unset — must be set in production) |
| `DATABASE_URL` | SQLAlchemy connection string | No (defaults to local SQLite) |
| `UPLOAD_FOLDER` | Where uploaded files land | No (defaults to `app/uploads`) |
| `MAX_UPLOAD_MB` | Upload size limit | No (defaults to 20) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth | Only if using Google sign-in |
| `INITIAL_ADMIN_EMAIL` | Bootstrap-promote this user to admin on startup | No (opt-in) |

## Immediate next steps (suggested)

1. Fix Google OAuth on production: add `ProxyFix`, get the Render app's
   exact URL from the user, register its `/auth/google/callback` in
   Google Cloud Console.
2. Ask the user to confirm the PDF preview black-box fix actually worked
   on their end.
3. Decide whether the ephemeral-filesystem issue (uploads wiped on
   redeploy) needs solving now or can wait.
