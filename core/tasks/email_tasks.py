"""Optional Celery task wrappers. Install/start Redis and Celery to use these."""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from core.models import EmailNotification, DeliveryAttempt

@shared_task(bind=True, max_retries=4, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True)
def deliver_notification(self, notification_id):
    notification=EmailNotification.objects.get(pk=notification_id)
    if notification.status=='sent':
        return {'status':'already_sent','notification_id':notification.pk}
    notification.attempts += 1
    try:
        accepted=send_mail(notification.subject,notification.body,settings.DEFAULT_FROM_EMAIL,[notification.recipient],fail_silently=False)
        if accepted != 1:
            raise RuntimeError('Configured email backend did not accept the notification')
        notification.status='sent'; notification.sent_at=timezone.now(); notification.last_error=''
        DeliveryAttempt.objects.create(notification=notification,success=True,detail='Accepted by configured backend; console mode is not inbox delivery')
        notification.save()
        return {'status':'accepted','notification_id':notification.pk}
    except Exception as exc:
        notification.status='failed'; notification.last_error=str(exc)[:2000]; notification.save()
        DeliveryAttempt.objects.create(notification=notification,success=False,detail=str(exc)[:2000])
        raise
