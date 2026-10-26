from django.core.management.base import BaseCommand
from core.models import EmailNotification
from core.services import queue_email
class Command(BaseCommand):
 help='Retry failed email notifications once using the configured backend.'
 def handle(self,*args,**opts):
  qs=EmailNotification.objects.filter(status='failed',attempts__lt=4)[:100]
  count=0
  for n in qs:
   # Reattempt the same event without creating a duplicate notification row.
   from django.core.mail import send_mail
   from django.conf import settings
   from django.utils import timezone
   from core.models import DeliveryAttempt
   n.attempts+=1
   try:
    sent=send_mail(n.subject,n.body,settings.DEFAULT_FROM_EMAIL,[n.recipient],fail_silently=False)
    if sent!=1: raise RuntimeError('Backend did not accept message')
    n.status='sent'; n.sent_at=timezone.now(); n.last_error=''
    DeliveryAttempt.objects.create(notification=n,success=True,detail='Retry accepted by configured backend'); count+=1
   except Exception as exc:
    n.last_error=str(exc)[:2000]; DeliveryAttempt.objects.create(notification=n,success=False,detail=n.last_error)
   n.save()
  self.stdout.write(f'Retried {count} notification(s); inspect EmailNotification for remaining failures.')
