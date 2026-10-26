import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class InternProfile(models.Model):
    ROLE_CHOICES=[('intern','Intern'),('mentor','Mentor'),('admin','Administrator')]
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='profile')
    intern_id=models.CharField(max_length=20,unique=True,blank=True)
    role=models.CharField(max_length=10,choices=ROLE_CHOICES,default='intern')
    project_details=models.CharField(max_length=240,blank=True)
    skills=models.TextField(blank=True)
    email_verified=models.BooleanField(default=False)
    onboarding_complete=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    def save(self,*args,**kwargs):
        if not self.intern_id and self.email_verified:
            self.intern_id='INT-'+uuid.uuid4().hex[:8].upper()
        super().save(*args,**kwargs)
    def __str__(self): return f'{self.intern_id or "Pending"} — {self.user.email}'

class Project(models.Model):
    name=models.CharField(max_length=160)
    description=models.TextField(blank=True)
    is_active=models.BooleanField(default=True)
    require_human_approval=models.BooleanField(default=True)
    passing_score=models.PositiveSmallIntegerField(default=70)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class ProjectMembership(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='memberships')
    intern=models.ForeignKey(InternProfile,on_delete=models.CASCADE,related_name='memberships')
    joined_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['project','intern'],name='unique_project_intern')]

class TaskTemplate(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='task_templates')
    title=models.CharField(max_length=180)
    description=models.TextField()
    instructions=models.TextField(blank=True)
    deliverables=models.TextField(blank=True)
    evaluation_criteria=models.JSONField(default=list,blank=True)
    sequence=models.PositiveIntegerField(default=1)
    difficulty=models.CharField(max_length=20,choices=[('beginner','Beginner'),('intermediate','Intermediate'),('advanced','Advanced')],default='beginner')
    deadline_days=models.PositiveIntegerField(default=7)
    is_required=models.BooleanField(default=True)
    is_active=models.BooleanField(default=True)
    class Meta:
        ordering=['sequence']
        constraints=[models.UniqueConstraint(fields=['project','sequence'],name='unique_project_task_sequence')]
    def __str__(self): return f'{self.project}: {self.title}'

class TaskDependency(models.Model):
    task=models.ForeignKey(TaskTemplate,on_delete=models.CASCADE,related_name='dependencies')
    prerequisite=models.ForeignKey(TaskTemplate,on_delete=models.CASCADE,related_name='unlocks')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['task','prerequisite'],name='unique_task_dependency')]

class ProjectMilestone(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='milestones')
    name=models.CharField(max_length=160)
    required_task_sequences=models.JSONField(default=list,blank=True)
    is_required=models.BooleanField(default=True)
    completed_at=models.DateTimeField(null=True,blank=True)

class TaskAssignment(models.Model):
    STATUS=[('not_started','Not Started'),('in_progress','In Progress'),('submitted','Submitted'),('under_review','Under Review'),('changes_requested','Changes Requested'),('approved','Approved'),('completed','Completed')]
    intern=models.ForeignKey(InternProfile,on_delete=models.CASCADE,related_name='assignments')
    task=models.ForeignKey(TaskTemplate,on_delete=models.PROTECT,related_name='assignments')
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='assignments')
    assigned_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='assigned_tasks')
    assigned_at=models.DateTimeField(auto_now_add=True)
    deadline=models.DateTimeField()
    status=models.CharField(max_length=24,choices=STATUS,default='not_started')
    is_revision=models.BooleanField(default=False)
    idempotency_key=models.CharField(max_length=80,unique=True,default=uuid.uuid4)
    class Meta:
        indexes=[models.Index(fields=['intern','status']),models.Index(fields=['project','deadline'])]
        constraints=[models.UniqueConstraint(fields=['intern','task'],condition=models.Q(is_revision=False),name='unique_initial_task_per_intern')]
    def __str__(self): return f'{self.intern} / {self.task.title}'

class Submission(models.Model):
    assignment=models.ForeignKey(TaskAssignment,on_delete=models.CASCADE,related_name='submissions')
    version=models.PositiveIntegerField(default=1)
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    file=models.FileField(upload_to='submissions/%Y/%m/',blank=True)
    repository_url=models.URLField(blank=True)
    deployed_url=models.URLField(blank=True)
    explanation=models.TextField(blank=True)
    submitted_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['assignment','version'],name='unique_submission_version')]
        ordering=['-version']

class EvaluationRubric(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='rubrics')
    name=models.CharField(max_length=120)
    version=models.PositiveIntegerField(default=1)
    criteria=models.JSONField(default=list)
    is_active=models.BooleanField(default=True)

class Review(models.Model):
    STATUS=[('scheduled','Scheduled'),('in_progress','In Progress'),('pending_human','Pending Human Review'),('approved','Approved'),('changes_requested','Changes Requested'),('rejected','Rejected'),('cancelled','Cancelled')]
    assignment=models.ForeignKey(TaskAssignment,on_delete=models.CASCADE,related_name='reviews')
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='reviews_to_conduct')
    scheduled_start=models.DateTimeField(null=True,blank=True)
    scheduled_end=models.DateTimeField(null=True,blank=True)
    timezone_name=models.CharField(max_length=64,default='Asia/Kolkata')
    status=models.CharField(max_length=24,choices=STATUS,default='scheduled')
    attendance_confirmed=models.BooleanField(default=False)
    notes=models.TextField(blank=True)
    decision_reason=models.TextField(blank=True)
    ai_score=models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True)
    ai_report=models.JSONField(default=dict,blank=True)
    human_approved_at=models.DateTimeField(null=True,blank=True)
    rubric_version=models.PositiveIntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)

class ReviewFeedback(models.Model):
    review=models.ForeignKey(Review,on_delete=models.CASCADE,related_name='feedback_items')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    body=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)

class RevisionRequest(models.Model):
    review=models.ForeignKey(Review,on_delete=models.CASCADE,related_name='revision_requests')
    instructions=models.TextField()
    deadline=models.DateTimeField(null=True,blank=True)
    resolved_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class CalendarEvent(models.Model):
    review=models.OneToOneField(Review,on_delete=models.CASCADE,related_name='calendar_event')
    provider=models.CharField(max_length=20,default='mock')
    external_event_id=models.CharField(max_length=240,blank=True)
    meeting_url=models.URLField(blank=True)
    status=models.CharField(max_length=20,default='pending')
    error_message=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class ChatConversation(models.Model):
    intern=models.ForeignKey(InternProfile,on_delete=models.CASCADE,related_name='conversations')
    assignment=models.ForeignKey(TaskAssignment,on_delete=models.CASCADE,related_name='conversations',null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    conversation=models.ForeignKey(ChatConversation,on_delete=models.CASCADE,related_name='messages')
    role=models.CharField(max_length=12,choices=[('user','User'),('assistant','Assistant'),('system','System')])
    content=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)

class EmailNotification(models.Model):
    STATUS=[('queued','Queued'),('sent','Accepted by provider'),('failed','Failed')]
    recipient=models.EmailField()
    subject=models.CharField(max_length=240)
    body=models.TextField()
    event_key=models.CharField(max_length=160,unique=True)
    status=models.CharField(max_length=20,choices=STATUS,default='queued')
    attempts=models.PositiveSmallIntegerField(default=0)
    provider_message_id=models.CharField(max_length=240,blank=True)
    last_error=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    sent_at=models.DateTimeField(null=True,blank=True)

class DeliveryAttempt(models.Model):
    notification=models.ForeignKey(EmailNotification,on_delete=models.CASCADE,related_name='delivery_attempts')
    success=models.BooleanField(default=False)
    detail=models.TextField(blank=True)
    attempted_at=models.DateTimeField(auto_now_add=True)

class WorkflowExecution(models.Model):
    key=models.CharField(max_length=180,unique=True)
    workflow=models.CharField(max_length=100)
    status=models.CharField(max_length=20,default='pending')
    attempts=models.PositiveSmallIntegerField(default=0)
    last_error=models.TextField(blank=True)
    updated_at=models.DateTimeField(auto_now=True)

class AuditLog(models.Model):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    action=models.CharField(max_length=100)
    object_type=models.CharField(max_length=100)
    object_id=models.CharField(max_length=80)
    details=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']

