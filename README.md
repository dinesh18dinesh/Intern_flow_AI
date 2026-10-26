# InternFlow AI — Internship Task Allocation, Review & Mentorship

A Django-based working MVP for verified intern accounts, relational task allocation, private submissions, review decisions, email delivery tracking, mentor/admin views, and an isolated task-assistant interface. The project intentionally **does not pretend external integrations are live**: email defaults to the development console backend, AI defaults to a labeled mock, and calendar records remain unscheduled until Google Calendar integration is configured.

## What works in this MVP

- Email-based registration, password validation, verification links, normalized duplicate-email checks, unique intern IDs after verification.
- Role-aware dashboard and Django Admin for project/task setup, intern records, assignments, submissions, reviews, and audit logs.
- Transactional first-eligible-task allocation with prerequisite and required-sequence checks; no duplicate initial assignment.
- Secure per-intern submission endpoint with file extension and size checks, repository/deployment URLs, and version history.
- Idempotent notification records and delivery attempts; development console email is clearly identified as not real inbox delivery.
- Human review decisions, audit trail, approval-gated next-task progression, and notification of next task.
- Task-scoped chatbot history with intern ownership checks and explicit mock response.
- Review placeholder that does not invent calendar times or Meet URLs.
- Demo seed command for 100 test interns and sample task sequence.
- Automated tests for allocation, progression, intern isolation, and duplicate registration.

## Important implementation boundary

This is a runnable MVP foundation, not a claim that every requested production integration is complete. The following require additional provider-specific implementation and live credential verification before production: Gmail API OAuth, Google Calendar free/busy and conference creation, live LLM prompting/document parsing, antivirus scanning, cloud object storage, Excel export, automated recurring reminder scheduler, production rate-limit backend, and load testing at 100 concurrent users. The code fails closed for calendar and AI rather than fabricating successful results. Use a staging environment and security review before storing real intern data.

## Quick start (Windows PowerShell)

```powershell
cd path\to\internship_task_bot
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Development email messages and verification links appear in the terminal because `EMAIL_MODE=console`. Click the printed verification link before signing in as an intern.

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Seed demo records

```bash
python manage.py seed_demo --interns 100
```

Creates one sample project, three ordered tasks and up to 100 demo intern accounts. Newly created demo accounts use `DemoPass!12345`; these are test-only identities using `example.test` addresses and must never be used for production. Seeded users are active and email-verified to make demo login possible.

For a single sample login, copy the demo credentials from `.env.example` into your ignored local `.env`, then run `python manage.py seed_demo --interns 1`. Sign in using `DEMO_LOGIN_EMAIL` and `DEMO_LOGIN_PASSWORD`; the login redirects to the dashboard. These credentials are for local demonstration only.

## Allocate a task

Create a project, task templates and project memberships in `/admin/`. Allocation service example from Django shell:

```bash
python manage.py shell
```

```python
from core.models import InternProfile, Project
from core.services import allocate_next_task
intern = InternProfile.objects.get(user__email='demo.intern001@example.test')
project = Project.objects.get(name='AI Web Development Internship')
assignment = allocate_next_task(intern, project)
print(assignment)
```

For production, invoke the same service from an authorized admin action or a Celery task with an idempotency key and structured error handling. The initial MVP exposes project/task management via Django Admin rather than a full custom task-authoring wizard.

## Run tests

```bash
python manage.py test core
```

The tests use Django's test database and do not send real email, call an LLM, or create Google Calendar events. These are mock/local tests, not live integration tests.

## Environment configuration

See `.env.example`. `DJANGO_SECRET_KEY` must be a strong random secret in deployment; `DJANGO_DEBUG=False`; set `DJANGO_ALLOWED_HOSTS` to exact hostnames; use PostgreSQL `DATABASE_URL`; configure a real SMTP account or implement/enable Gmail API OAuth. Keep credentials out of Git. The included `EMAIL_MODE=smtp` uses Django SMTP and therefore confirms only backend acceptance, not recipient inbox delivery. Google Meet URLs must come from a confirmed Google Calendar API conference response, not a generated placeholder.

### Gmail SMTP

For a managed Google Workspace/Gmail account, use a supported app password if the account policy permits it, or implement Gmail API OAuth for organizational deployments. Do not use the account's normal password. Set `EMAIL_MODE=smtp`, `EMAIL_HOST`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`. Run a controlled delivery test before enabling reminders.

### Google Calendar and Meet

1. Create a Google Cloud project and enable Google Calendar API.
2. Configure the OAuth consent screen and authorized redirect URI.
3. Request only the scopes required to read availability and create/update events, for example calendar event management; confirm exact scopes against your organization policy.
4. Store OAuth client secrets and refresh tokens securely on the server; never commit them.
5. Implement free/busy lookup, event creation with `conferenceDataVersion=1`, and check the API response for a confirmed `hangoutLink`/conference entry point.
6. Persist external event IDs; use idempotency keys; handle cancellation/reschedule API calls and revoked credentials.
7. Do not invite interns until the calendar event and meeting link are confirmed.

The current build creates an unscheduled review record and a `CalendarEvent` with `needs_configuration`. It does not create a fake link.

### Live AI provider

`AI_MODE=mock` is the default. `core/ai.py` deliberately labels mock replies and refuses to produce fabricated evaluation scores. Before enabling a live provider, implement a provider adapter with explicit data minimization, task/document context boundaries, output schema validation, prompt-injection defenses for submitted files, token/time limits, and human approval. Never execute uploaded code on the web worker; use an isolated sandbox if code execution is required.

## Production checklist

- PostgreSQL, Redis, Celery worker and Celery Beat with monitored queues.
- HTTPS, strong secrets, secure cookies, exact allowed hosts, error reporting and structured logs with PII redaction.
- Private object storage and short-lived authorized download links; malware scanning and content/MIME validation.
- Real provider adapters and live integration tests in staging.
- Transactional outbox or durable queue pattern for DB updates plus external notifications.
- Review capacity, working-hours, time-zone, holiday, conflict and rescheduling policies.
- Backups, restore drills, retention/deletion rules, access review and incident response.
- Load test registration, dashboard, upload and allocation concurrency for 100 interns.
- Set staff users with `is_staff=True` and set their `InternProfile.role` to `admin` or `mentor` as appropriate. Protect `/admin/` with strong credentials and MFA at the identity-provider/organizational level.

## Known MVP limitations

- Admin project/task editing is through Django Admin, not a custom visual workflow builder.
- CSV bulk import and Excel export are not wired into the UI yet.
- Review creation is intentionally unscheduled; calendar availability, real Meet generation, reminder jobs and rescheduling are not implemented as live integrations.
- AI chatbot and rubric evaluator are adapter stubs/mock mode; uploaded documents are not parsed and source code is not executed.
- Upload extension and size checks are basic safeguards, not a malware scanner; deploy behind private storage and add MIME/content scanning.
- `core/management/commands/retry_failed_emails.py` offers a bounded manual retry command; production delivery should use Celery with exponential backoff and a durable outbox.
- Do not expose `MEDIA_URL` publicly in production. Serve private submissions only after authorization.
