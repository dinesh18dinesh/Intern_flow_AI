# Architecture and Workflow

## Trust boundaries

- Browser sessions authenticate the user; email is a contact/username identifier, not proof of identity until the verification token is redeemed.
- Every intern submission and chat endpoint filters by the authenticated intern profile. Staff-only review decisions check role permissions server-side.
- Submitted files and text are untrusted input. Do not execute submitted code on the application host. Production storage must be private and scanned.
- AI output is advisory and should never update a final task decision directly. Human decision controls progression when approval is required.
- Email and calendar integrations are external side effects. Persist an idempotency key and delivery/event IDs before building retry automation.

## Core relational links

- `User 1—1 InternProfile`
- `Project 1—N TaskTemplate`, `Project N—N InternProfile` through `ProjectMembership`
- `TaskTemplate N—N TaskTemplate` through `TaskDependency`
- `InternProfile + Project + TaskTemplate → TaskAssignment`
- `TaskAssignment 1—N Submission`, `TaskAssignment 1—N Review`
- `Review 1—1 CalendarEvent`, `Review 1—N ReviewFeedback/RevisionRequest`
- `InternProfile + TaskAssignment → ChatConversation 1—N ChatMessage`
- `EmailNotification 1—N DeliveryAttempt`
- `WorkflowExecution` and `AuditLog` support retry/idempotency and history.

## Allocation rules

1. Only active task templates are candidates.
2. Do not allocate an already assigned initial task.
3. Explicit prerequisites must be approved/completed.
4. Earlier required tasks in sequence must be approved/completed.
5. Assignment creation is transaction-wrapped and protected by a database uniqueness constraint.
6. Approval marks the assignment completed and then asks the allocator for the next eligible task.

## Review rules

- `scheduled` means a review record exists; it does not mean a calendar slot is confirmed.
- `CalendarEvent.status=needs_configuration` means no confirmed meeting link exists.
- Do not send a meeting invitation until Google Calendar confirms the event and conference URL.
- An approval decision records the human approver and decision time. Task progression is triggered only from the approval service.

## Provider readiness matrix

| Capability | Default mode | Production requirement |
|---|---|---|
| Email | Console backend | SMTP/Gmail API credentials and live delivery test |
| Calendar/Meet | Explicit mock/configuration-needed record | OAuth, free/busy, event creation, confirmed conference URL, cancellation/reschedule |
| AI chat | Labeled mock | Provider adapter, data policy, safe prompt construction and output validation |
| AI evaluation | No score in mock mode | Document extraction, rubric schema, evidence references, human approval |
| Uploads | Local dev folder | Private object storage, authorization, content scanning and retention policy |
| Background jobs | Optional Celery task wrapper | Redis, worker/beat, durable retries, monitoring and alerting |
