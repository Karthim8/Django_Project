# Accounts App Documentation

The `accounts` app is the specialized identity and developer-profiling engine of the NexusLink project. It manages custom user registration via OTP, extended user profiles, GitHub OAuth integration, background fetching of GitHub stats, and AI-powered evaluation using Google Gemini.

## 1. Architecture

The app is built using Django and relies heavily on external services and asynchronous task processing.

### Key Components

*   **Django Views:** Handle user registration and OTP verification.
*   **Django Models:** Store user profiles, GitHub data, AI evaluation scores, and placement badges.
*   **Celery & Redis (Upstash):** Manage asynchronous background tasks (GitHub API fetching, AI evaluation) and temporary OTP storage.
*   **Django Channels (WebSockets):** Push real-time progress updates to the frontend during the evaluation process.
*   **External APIs:**
    *   **Brevo (Sendinblue):** For sending OTP emails.
    *   **GitHub API:** For fetching developer statistics (repos, commits, PRs, languages).
    *   **Google Gemini AI:** For evaluating developer profiles based on GitHub data.

## 2. Data Flow & Endpoints

### Flow A: Registration & OTP Verification

This flow bypasses the database for temporary OTP storage, opting for high-speed Redis instead.

1.  **Signup Form Submission**
    *   **Endpoint:** `POST /accounts/signup/`
    *   **View Logic (`views.custom_signup`):** Extracts name, email, and password. Creates an inactive `User` instance. Generates a 6-digit OTP.
    *   **Redis Storage:** Stores the OTP in Upstash Redis (`otp:<email>`) with a 5-minute timeout.
    *   **Email Dispatch:** Calls the Brevo API to send the OTP email.
    *   **Response:** Renders the verification page (`account/verify_sent.html`).

2.  **OTP Verification**
    *   **Endpoint:** `POST /accounts/verify-otp/`
    *   **View Logic (`views.verify_otp`):** Extracts the submitted OTP. Fetches the stored OTP from Upstash Redis. If they match, the `User` is marked active, logged in, and the OTP is deleted from Redis.
    *   **Response:** Redirects to the homepage (`/`) on success, or returns an error message on failure.

### Flow B: GitHub Login → AI Evaluation

This is a complex, asynchronous pipeline designed to prevent the web server from blocking while waiting for external API limits.

1.  **OAuth Login Signal**
    *   When a user logs in via GitHub OAuth, `django-allauth` fires a signal (handled in `signals.py`, not shown in the immediate file list but inferred from the prompt).
    *   **Profile Initialization:** Creates a `DeveloperProfile` with a `pending` status.
    *   **Task Delegation:** Triggers the Celery task `evaluate_github_profile.delay(user.id)`.

2.  **Celery Task Boot (`tasks.evaluate_github_profile`)**
    *   **Authentication:** Retrieves the user's GitHub OAuth token from `django-allauth`.
    *   **WebSocket Progress Push:** At various stages, calls `push_update()` to emit WebSocket messages (`evaluation_<username>`) to the frontend for real-time progress.

3.  **GitHub API Fetching**
    *   Fetches non-forked repositories.
    *   Iterates through repos to gather data (languages, total commits, READMEs, stars).
    *   Searches for merged Pull Requests to determine Open Source contributions.

4.  **Anti-Cheat Execution (`tasks.run_anticheat`)**
    *   Analyzes commit frequency and messages.
    *   Flags suspicious behavior (e.g., burst commits, high ratio of low-quality commit messages).

5.  **Gemini AI Evaluation**
    *   Formats the raw data (repos, languages, streak, PRs, anti-cheat flags) into a prompt.
    *   Sends the prompt to the `gemini-2.5-flash-lite` model, requesting a strict JSON response with scores for consistency, complexity, collaboration, etc.

6.  **Database Commit & Leaderboard Sync**
    *   Parses the AI JSON response.
    *   Updates the `DeveloperProfile` with scores, badges, and sets status to `complete`.
    *   Calls `update_all_ranks()` to recalculate global and campus rankings.
    *   Pushes a `leaderboard_update` WebSocket message to all connected clients.

## 3. Models

### `UserProfile`
Extends the default Django `User` model with additional details:
*   `role` (Student, Senior, Alumni)
*   `college`, `branch`, `batch_year`, `semester`
*   `github`, `codeforces`, `linkedin` URLs
*   `skills` (JSON array)

### `DeveloperProfile`
Stores the bulk of the GitHub analysis and AI evaluation:
*   **Raw GitHub Data:** `total_repos`, `total_commits`, `languages_used`, `commit_streak`, `commit_map`, etc.
*   **AI Scores:** `overall_score`, `consistency_score`, `complexity_score`, etc.
*   **Rank Info:** `rank_title`, `global_rank`, `campus_rank`, `badges`, etc.
*   **Anti-Cheat:** `spam_ratio`, `commits_per_day`, `is_suspicious`, `cheat_flags`.
*   **Status:** `evaluation_status` (pending, fetching, analyzing, complete, failed).

### `PlacementBadge`
Tracks user placements (company, role, package, year).

### `EmailVerification`
Used for alternative email verification (though Upstash Redis is currently used in the primary flow).

## 4. Dependencies & Services
*   **django-allauth:** GitHub OAuth integration.
*   **Celery:** Asynchronous background tasks.
*   **Redis (Upstash REST API):** Fast OTP storage.
*   **Brevo (Sendinblue) API:** Transactional email delivery.
*   **PyGithub:** Interacting with the GitHub API.
*   **Google Generative AI (Gemini):** AI profile evaluation.
*   **Django Channels:** WebSocket communication for live progress.
