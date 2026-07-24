# CampusNotes — Project Status

_Last updated: 2026-07-23. Written as a handoff/context snapshot — if you're
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
- PDF inline preview (iframe) + download. Originally paired with a
  premium-flag lock (UI/logic only, no payment integration) per the
  original spec; that lock was later removed entirely by explicit request
  — see "Premium-lock feature removed entirely" below. All
  resources are freely viewable/downloadable now.
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
- **Catalog simplified to University-only admin management.** Course,
  Semester, and Subject are all free text on the upload form now — typing a
  name/number looks it up or creates it automatically under the chosen
  parent (University → Course → Semester → Subject), same lookup-or-create
  pattern all the way down. University is the only level still admin-managed
  (small, stable list — the admin catalog page at `/admin/catalog` is now
  just an add-university form, no more Course/Semester/Subject forms). This
  was a multi-step conversion across several sessions: Subject went free
  first (briefly with `<datalist>` suggestions, then plain text), then
  Semester, then finally Course + the University dropdown becoming a real
  submitted form field. The old `cascade.js` (University → Course JS
  cascade) and its three `/api/courses` / `/api/semesters` / `/api/subjects`
  JSON endpoints are gone — nothing left to cascade once Course is free
  text too.
- About Us page
- **"Mark as Premium" checkbox removed from the upload form** (an earlier,
  smaller step — the field could no longer be *set* on new uploads, but
  the lock enforcement itself was still active for existing premium
  resources at the time). **Superseded later the same day by removing the
  premium-lock feature entirely** — see "Premium-lock feature removed
  entirely" further down. Noted here only to avoid confusion if this
  smaller step is found referenced elsewhere (e.g. old commit messages).
- **`user_type` field (Student/Faculty) — separate from `role`.**
  `role` (`student`/`admin`) gates admin permissions and is unaffected;
  `user_type` is a new, independent column that's just a public "who is
  this" label. Required choice at signup (`SignupForm`), editable later in
  Settings (`ProfileForm`) — both share one `USER_TYPE_CHOICES` list in
  `app/auth/forms.py`. Google sign-ups don't go through `SignupForm` (same
  as they already skip university/course), so they silently get the
  column's `server_default` of `"student"`, editable later in Settings —
  consistent with how the rest of the profile already works for Google
  accounts. Shown as a `.badge-student`/`.badge-faculty` badge (new CSS,
  parallel to the existing `.badge-verified`/`.badge-premium` pattern)
  next to the user's name on: their own account page (next to, and
  visually distinct from, the existing role badge), their public profile
  (see below), resource detail pages, the admin dashboard's pending-review
  list, and Home/Search resource cards.
- **Public user profiles at `/users/<id>`.** New `main.user_profile` route
  (public, no login required — same precedent as the existing public
  `/auth/avatar/<id>` route). Shows name, avatar, `user_type` badge,
  University/Course (only if set), their uploads, and a total upload
  count. Deliberately shows nothing else — email, password_hash, `role`,
  and `google_sub` are never referenced in the template, so there's no
  filtering logic to get wrong, they're just not there. Every place an
  uploader's name appears (Home/Search cards, resource detail pages, the
  admin dashboard) now links to this page.
- **Resource-card markup factored into a shared macro**
  (`macros.resource_card(r, show_uploader=True)` in
  `app/templates/macros.html`), used by Home, Search, "My uploads"
  (`account.html`), and the new public profile page — previously
  duplicated inline in the first three, and would have become a 4th
  duplicate. `show_uploader=False` on `account.html`'s and the profile
  page's own upload lists, since the uploader is already implied by page
  context there.
- **Star rating system.** New `Rating` model (`user_id`, `resource_id`,
  `stars` 1-5, `created_at`) with `uq_rating_user_resource` (one rating per
  user per resource) and `ck_rating_stars_range` (DB-level 1-5 check) —
  both verified by direct SQL that they actually reject violations, not
  just present in the model. App-level upsert in
  `resources.rate` (`POST /resources/<id>/rate`) is the primary "one
  rating per user" mechanism (query existing → update `.stars`, else
  create), same lookup-or-create shape as Course/Semester/Subject; the
  constraint is the backstop. Rejects rating your own upload (checked
  server-side in the route itself, not just hidden in the UI — verified
  with a forged POST that bypassed the template entirely and still got
  rejected with zero rows created). Originally also hid the widget for
  premium-locked resources; that condition was removed along with the
  premium-lock feature itself (see below) — rating is now available for
  every resource except your own. `Resource.average_rating` / `.rating_count` are plain Python
  properties over the `ratings` backref (sum/len in Python, one query per
  resource) — deliberately consistent with the app's existing
  N+1-lazy-relationship style elsewhere (e.g. `resource.subject.semester.
  course.university` chains in templates), not a special-cased optimized
  path just for ratings. Displayed as "4.3 ★ (12 ratings)" on Home/Search
  cards (via the shared macro, above) and resource detail pages; omitted
  entirely from cards with zero ratings to keep listings clean (detail
  pages show an explicit "No ratings yet" instead). Public profiles show
  combined "uploader reputation" — average across every rating on every
  one of that user's uploads, computed in Python over the already-fetched
  uploads list (no extra query). The star widget itself is a CSS-only
  radio-input trick (see `.star-rating` in `style.css`) wired to
  auto-submit on click (`onchange="this.form.submit()"`, same pattern as
  the Home/Search filter dropdowns) — no new JS file, consistent with the
  app's mostly-vanilla-JS style throughout.
- **Premium-lock feature removed entirely.** All resources are now freely
  viewable/downloadable regardless of `is_premium` — `_is_premium_locked()`
  (`app/resources/routes.py`) is deleted, along with every call site
  (`detail()`, `rate()`, `download()`, `preview()`) and every "locked" UI
  branch (the Premium badge on cards and the detail page, the "payments
  aren't set up" message, the `not locked` conditions gating the rating
  widget). Verified by temporarily flipping a real resource's `is_premium`
  to `True` and confirming an anonymous, logged-out viewer could still see
  no Premium badge, hit `/resources/<id>/preview` and get `200 OK` instead
  of `403`, and see Download/Preview rendered unconditionally — this used
  to be the single strictest case the old lock enforced (anonymous +
  premium = always locked), so it was the right case to check. Flag
  reverted to `False` afterward. **`is_premium` the column stays** —
  informational only now (see `models.py` comment on the column), kept
  because it's one boolean with real data already in production and the
  natural hook if a real payment feature gets built later; dropping it
  would need a migration for no present benefit. No migration needed for
  the removal itself, since nothing about the column or schema changed —
  only the enforcement logic and UI.
- **Comment system.** New `Comment` model (`user_id`, `resource_id`,
  `body` Text, `created_at`), no unique constraint (unlike `Rating` —
  multiple comments per user per resource are expected). Any logged-in
  user can post (`POST /resources/<id>/comments`); delete
  (`POST /resources/<id>/comments/<comment_id>/delete`) is restricted to
  the comment's author or an admin, `403` otherwise — verified three ways
  in the browser/via a test client: a non-owner non-admin's forged delete
  attempt correctly got `403` with the comment surviving untouched; the
  author deleting their own comment through the real UI worked; and an
  admin deleting a comment they didn't author (via the real UI, not a
  script — the CSRF-token plumbing in a raw test-client POST is fiddly
  enough that the real browser flow was the trustworthy check) also
  worked. Comments show most-recent-first, each with the author's name +
  `user_type` badge (linked to their public profile, same treatment as
  the uploader byline elsewhere) and a `%b %d, %Y`-formatted timestamp —
  the first place in the app that displays a date/time at all. Comments
  are *not* gated by `is_premium` in any way (that condition doesn't
  exist anymore — see above), and deliberately weren't given a
  lock-style special case even conceptually: a comment section reads more
  like discussion than "consuming the content."

**Deployment readiness work:**
- `requirements.txt` is a full pinned lockfile (`pip freeze` output, not
  just top-level deps) — includes `gunicorn` and `psycopg2-binary`
- `DATABASE_URL` / `SECRET_KEY` confirmed read from env vars; `postgres://`
  URLs auto-normalized to `postgresql://` (some hosts still hand out the
  old scheme, which modern SQLAlchemy rejects)
- `db.create_all()` runs automatically on every app startup (idempotent,
  wrapped in try/except) — no Shell access to run migrations by hand
- **Flask-Migrate is now actually initialized** (`migrations/` was an empty
  placeholder before this session — `flask db init` was never run). Four
  migrations exist so far, chained in order: `a79e6c917800` drops
  `University.location` and adds a case-insensitive unique index on
  `Course(university_id, lower(name))`; `c43d354413b9` adds
  `User.user_type` (`server_default='student'`, so it backfills existing
  rows cleanly — confirmed against local dev's 3 existing users);
  `937502be882e` creates the `ratings` table; `786fcdaff5cd` creates the
  `comments` table. All four were reviewed as a diff before being applied.
  `flask_migrate.upgrade()` runs in-process on every app startup, right
  after `db.create_all()`, same no-Shell-access rationale — Alembic tracks
  the applied revision in an `alembic_version` table so it's idempotent and
  a no-op once current. This is the mechanism that will make future schema
  changes (not just this one) reach Render without Shell access.
  - **Gotcha discovered while writing `937502be882e`, confirmed again on
    `786fcdaff5cd`, worth knowing before writing the *next* "add a whole
    new table" migration**: `db.create_all()` and `migrate.upgrade()` both
    run on *every* startup, `create_all()` first. For a migration that
    only alters an *existing* table (the first two above), that's
    harmless — `create_all()` never touches existing tables. But for a
    migration that creates a brand-new table, `create_all()` always wins
    the race and creates it first (that's exactly what `create_all()` is
    for), so an unconditional `op.create_table()` in the migration then
    fails with "already exists" on literally every fresh environment,
    including the first production deploy after such a migration ships.
    Worse: that failure is caught by the startup try/except (logged, not
    raised), so `alembic_version` silently never advances — every
    subsequent restart repeats the same failed attempt forever, and it
    permanently blocks any migration chained after it. `937502be882e` hit
    this locally first (caught before it ever reached production) and was
    fixed by making the migration check for the table's existence before
    creating it; `786fcdaff5cd` was written with that same guard from the
    start, no back-and-forth needed the second time. **Any future
    migration that creates a new table needs this same existence-check
    guard**, not just a plain `op.create_table()` — this is now the
    established pattern, not a one-off fix.
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

2. **Catalog field history (Subject → Semester → Course, all now free
   text) — done, full history preserved here since it changed shape
   several times across sessions and is easy to misremember:**
   - **Subject**: (a) originally a `<select>` dropdown populated via
     cascading JS, (b) changed to free text with `<datalist>` autocomplete
     suggestions pulled from existing subjects in the chosen semester, (c)
     datalist suggestions removed — plain text input, no autocomplete.
     Backend logic (case-insensitive lookup-or-create against the chosen
     semester) has been stable since (b).
   - **Semester**: converted from a JS-cascaded dropdown (`semester_id`) to
     a plain number input (`semester_number`, `IntegerField`, 1–20).
     Lookup-or-create against `Semester.query.filter_by(course_id=...,
     number=...)`, backed by the pre-existing `uq_semester_course_number`
     unique constraint.
   - **Course**: converted from an admin-managed dropdown (with its own
     `/admin/catalog` create form) to a plain text input
     (`course_name`). Lookup-or-create is case-insensitive
     (`lower(name)` match under the chosen university), backed by a new
     case-insensitive unique index, `uq_course_university_name_ci` on
     `(university_id, lower(name))` — see the migration note above. The
     admin `CourseForm`/`SemesterForm`/`SubjectForm` and their
     `create_course`/`create_semester`/`create_subject` routes are all
     deleted; `/admin/catalog` now only manages University.
   - **University**: became a real submitted form field on upload
     (`university_id`, `SelectField`, choices populated server-side) —
     previously it was a JS-only select whose value was never submitted
     (Course was resolved from a JS-cascaded `course_id` instead). It
     remains the only catalog level admins manage directly.
   - Home/Search page filters are untouched throughout all of this — they
     build their Course/Semester dropdowns via direct SQLAlchemy queries in
     `app/main/routes.py`, not the JSON API endpoints, since those pages
     filter *existing* data rather than create new rows.
   - Verified end-to-end in the browser each step of the way, most recently:
     typing a brand-new course name ("BTech") on upload created the
     Course/Semester/Subject chain automatically with zero admin setup;
     re-submitting with different case ("btech") reused the same Course row
     instead of creating a duplicate (confirmed via direct DB query).

3. **Before the Course unique index was added, production was checked for
   pre-existing duplicates** (case-insensitive `(university_id, name)`
   collisions) via a one-off read-only script run locally against Render's
   External Database URL — **none found**, so the index could be added
   directly with no dedup pass needed on production. (Local dev *did* have
   one duplicate — an empty leftover "BCA" course from earlier ad-hoc
   testing — cleaned up with a one-off merge script before the migration
   ran locally.) Also confirmed: the one `University.location` value that
   existed in production (`"Nagaland University" → "Nagaland"`) is fine to
   lose; dropping the column was intentional, not an oversight.

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
- **Real migration history now exists** (see "Deployment readiness work"
  above) — this used to say Flask-Migrate was installed but never
  initialized; that's resolved as of migration `a79e6c917800`. Going
  forward, schema changes that `db.create_all()` can't handle (drop/alter a
  column, add an index/constraint) need a real `flask db migrate` +
  reviewed migration file, not a DB wipe-and-reseed. `flask_migrate.upgrade()`
  running on every startup means these now reach Render without Shell
  access, same as `db.create_all()` always has.
- **Admin catalog page is create-only, University-only** — no edit/delete,
  and Course/Semester/Subject aren't managed there at all anymore (they're
  free-text lookup-or-create on the upload form instead — see "In progress"
  above). Explicit scope boundary from the user's request, not a bug.
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
4. **Watch the first production deploy after these migrations land** — none
   of `a79e6c917800` (catalog simplification), `c43d354413b9`
   (`user_type`), `937502be882e` (`ratings` table), or `786fcdaff5cd`
   (`comments` table) have reached production yet, all four are only
   applied locally so far. Production was pre-checked for duplicate-Course
   rows ahead of the first one and confirmed clean (see "In progress"
   above); the second is a straightforward additive column with a
   `server_default`; the third and fourth both create a brand-new table
   and are both written with the create_all()-race existence-check guard
   from the start (the third needed a fix-and-retry locally to discover
   this; the fourth applied cleanly on the first attempt using the same
   guard). All four should apply cleanly via the `flask_migrate.upgrade()`
   startup hook — but this is the first time this project has ever run
   real migrations against production, so it's worth confirming the
   Render deploy logs show all four applying successfully, in order,
   rather than assuming.
