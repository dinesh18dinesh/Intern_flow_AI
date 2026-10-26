from django.contrib import admin
from .models import *
@admin.register(InternProfile)
class InternProfileAdmin(admin.ModelAdmin): list_display=('intern_id','user','role','email_verified','created_at'); search_fields=('intern_id','user__email','user__first_name'); list_filter=('role','email_verified')
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin): list_display=('name','is_active','require_human_approval','passing_score')
@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin): list_display=('title','project','sequence','difficulty','deadline_days','is_active'); list_filter=('project','difficulty','is_active'); search_fields=('title','description')
@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin): list_display=('intern','task','project','status','deadline','assigned_at'); list_filter=('status','project'); search_fields=('intern__user__email','task__title')
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin): list_display=('assignment','version','uploaded_by','submitted_at')
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin): list_display=('assignment','reviewer','status','scheduled_start','attendance_confirmed'); list_filter=('status',)
for model in [ProjectMembership,TaskDependency,ProjectMilestone,EvaluationRubric,ReviewFeedback,RevisionRequest,CalendarEvent,ChatConversation,ChatMessage,EmailNotification,DeliveryAttempt,WorkflowExecution,AuditLog]:
    try: admin.site.register(model)
    except admin.sites.AlreadyRegistered: pass
admin.site.site_header='Internship Workflow Administration'
admin.site.site_title='Internship Admin'
