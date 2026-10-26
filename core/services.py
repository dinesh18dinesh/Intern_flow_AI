from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .models import TaskAssignment, AuditLog, EmailNotification, DeliveryAttempt, CalendarEvent, Review

@transaction.atomic
def allocate_next_task(intern, project, actor=None):
    """Allocate the first eligible task transactionally; never duplicate a non-revision assignment."""
    assigned=set(TaskAssignment.objects.filter(intern=intern,project=project,is_revision=False).values_list('task_id',flat=True))
    for task in project.task_templates.filter(is_active=True).order_by('sequence'):
        if task.id in assigned: continue
        prerequisites=list(task.dependencies.values_list('prerequisite_id',flat=True))
        if prerequisites:
            done=set(TaskAssignment.objects.filter(intern=intern,task_id__in=prerequisites,status__in=['approved','completed']).values_list('task_id',flat=True))
            if not set(prerequisites).issubset(done): continue
        # Respect sequential task ordering even if explicit dependencies were omitted.
        earlier_required=project.task_templates.filter(is_active=True,is_required=True,sequence__lt=task.sequence)
        if any(not TaskAssignment.objects.filter(intern=intern,task=t,status__in=['approved','completed']).exists() for t in earlier_required):
            continue
        assignment=TaskAssignment.objects.create(intern=intern,project=project,task=task,assigned_by=actor,deadline=timezone.now()+timedelta(days=task.deadline_days),idempotency_key=f'assign:{intern.pk}:{task.pk}')
        AuditLog.objects.create(actor=actor,action='task_allocated',object_type='TaskAssignment',object_id=str(assignment.pk),details={'intern_id':intern.pk,'task_id':task.pk,'project_id':project.pk})
        return assignment
    return None

def queue_email(recipient, subject, body, event_key):
    """Idempotently create a notification record and attempt delivery. Console backend is explicitly a dev mock."""
    notification,created=EmailNotification.objects.get_or_create(event_key=event_key,defaults={'recipient':recipient,'subject':subject,'body':body})
    if not created and notification.status=='sent': return notification
    notification.attempts += 1
    try:
        count=send_mail(subject,body,settings.DEFAULT_FROM_EMAIL,[recipient],fail_silently=False)
        if count != 1: raise RuntimeError('Email backend did not accept the message.')
        notification.status='sent'; notification.sent_at=timezone.now()
        detail='Accepted by configured Django email backend'
        if settings.EMAIL_MODE!='smtp': detail='Printed by development console backend; NOT delivered to a real inbox'
        DeliveryAttempt.objects.create(notification=notification,success=True,detail=detail)
    except Exception as exc:
        notification.status='failed'; notification.last_error=str(exc)[:2000]
        DeliveryAttempt.objects.create(notification=notification,success=False,detail=str(exc)[:2000])
    notification.save()
    return notification

def schedule_review(assignment, reviewer=None):
    """Safe development placeholder. It deliberately does not fabricate a Meet URL."""
    review=Review.objects.create(assignment=assignment,reviewer=reviewer,status='scheduled',scheduled_start=None,scheduled_end=None)
    CalendarEvent.objects.create(review=review,provider=settings.GOOGLE_INTEGRATION_MODE,status='needs_configuration',error_message='No confirmed calendar slot. Configure Google OAuth and reviewer availability before inviting the intern.')
    AuditLog.objects.create(actor=reviewer,action='review_created_unscheduled',object_type='Review',object_id=str(review.pk),details={'assignment_id':assignment.pk})
    return review

def finalize_review(review, decision, actor, reason=''):
    """Only authorized human decision handlers should call this after enforcing permissions."""
    from django.db import transaction
    with transaction.atomic():
        review=Review.objects.select_for_update().select_related('assignment__intern','assignment__project').get(pk=review.pk)
        if decision=='approved':
            review.status='approved'; review.human_approved_at=timezone.now(); review.decision_reason=reason
            review.assignment.status='completed'; review.assignment.save(update_fields=['status'])
        elif decision=='changes_requested':
            review.status='changes_requested'; review.decision_reason=reason
            review.assignment.status='changes_requested'; review.assignment.save(update_fields=['status'])
        elif decision=='rejected':
            review.status='rejected'; review.decision_reason=reason
        else: raise ValueError('Unsupported review decision')
        review.save()
        AuditLog.objects.create(actor=actor,action='review_decision',object_type='Review',object_id=str(review.pk),details={'decision':decision,'reason':reason[:500]})
        if decision=='approved':
            next_assignment=allocate_next_task(review.assignment.intern,review.assignment.project,actor=actor)
            if next_assignment:
                body = (f"Hello {review.assignment.intern.user.get_full_name() or review.assignment.intern.user.username},\n\n"
                        f"Your next task is {next_assignment.task.title}. Deadline: {timezone.localtime(next_assignment.deadline)}.\n"
                        "Sign in to view instructions.")
                queue_email(review.assignment.intern.user.email, f'Next task assigned: {next_assignment.task.title}', body, 'next-task:%s' % next_assignment.pk)
        return review
