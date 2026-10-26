import csv
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.views.decorators.http import require_POST
from .forms import RegistrationForm, SubmissionForm
from .models import InternProfile, Project, ProjectMembership, TaskAssignment, Submission, Review, ChatConversation, ChatMessage, AuditLog
from .tokens import email_verification_token
from .services import allocate_next_task, queue_email, schedule_review, finalize_review
from .ai import answer_task_question, evaluate_submission

def home(request):
    return render(request,'home.html')

def register(request):
    if request.user.is_authenticated: return redirect('dashboard')
    form=RegistrationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        data=form.cleaned_data
        user=User.objects.create_user(username=data['email'],email=data['email'],password=data['password'],first_name=data['full_name'].strip()[:150])
        user.is_active=False
        user.save(update_fields=['is_active'])
        InternProfile.objects.create(user=user,project_details=data['project_details'],skills=data['skills'])
        uid=urlsafe_base64_encode(force_bytes(user.pk)); token=email_verification_token.make_token(user)
        verify_url=request.build_absolute_uri(f'/verify/{uid}/{token}/')
        body = (f"Hello {user.first_name},\n\nVerify your email using this link: {verify_url}\n\n"
                "If you did not register, ignore this email.")
        notif=queue_email(user.email,'Verify your internship portal email',body,'verify:'+str(user.pk))
        messages.success(request,'Account created. Check the configured email channel for your verification link. In console development mode, the message is printed in the server terminal, not delivered to your inbox.')
        return redirect('login')
    return render(request,'register.html',{'form':form})

def verify_email(request,uidb64,token):
    try: user=User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (User.DoesNotExist,ValueError,TypeError): user=None
    if user and email_verification_token.check_token(user,token):
        user.is_active=True; user.save(update_fields=['is_active'])
        profile=user.profile; profile.email_verified=True; profile.save()
        AuditLog.objects.create(actor=user,action='email_verified',object_type='InternProfile',object_id=str(profile.pk))
        # Allocate the first task only if an administrator already placed this intern in a project.
        for membership in profile.memberships.select_related('project').filter(project__is_active=True):
            assignment=allocate_next_task(profile,membership.project)
            if assignment:
                queue_email(user.email, f'Task assigned: {assignment.task.title}',
                            f'Your first task is {assignment.task.title}. Deadline: {timezone.localtime(assignment.deadline)}. Sign in to view details.',
                            f'initial-task:{assignment.pk}')
                schedule_review(assignment)
        messages.success(request,'Email verified. You can now sign in. If you have been added to a project, the first eligible task will be allocated.')
    else: messages.error(request,'This verification link is invalid or expired. Please contact an administrator.')
    return redirect('login')

def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    error=''
    if request.method=='POST':
        email=request.POST.get('email','').strip()
        password=request.POST.get('password','')
        candidates=User.objects.filter(email__iexact=email)
        user=None
        for candidate in candidates:
            user=authenticate(request,username=candidate.username,password=password)
            if user: break
        if user:
            if hasattr(user,'profile') and user.profile.role=='intern' and not user.profile.email_verified:
                error='Please verify your email before signing in.'
            else: login(request,user); return redirect('dashboard')
        elif any(candidate.check_password(password) and hasattr(candidate,'profile') and candidate.profile.role=='intern' and not candidate.profile.email_verified for candidate in candidates):
            error='Please verify your email before signing in.'
        else: error='Email or password is incorrect, or the account is not verified.'
    return render(request,'login.html',{'error':error})

def logout_view(request):
    logout(request); return redirect('home')

@login_required
def dashboard(request):
    profile=getattr(request.user,'profile',None)
    if request.user.is_superuser or (profile and profile.role in ['admin','mentor']):
        assignments=TaskAssignment.objects.select_related('intern__user','project','task').all().order_by('-assigned_at')[:100]
        context={'is_admin':True,'total_interns':InternProfile.objects.filter(role='intern',email_verified=True).count(),'active_projects':Project.objects.filter(is_active=True).count(),
          'pending_tasks':TaskAssignment.objects.filter(status__in=['not_started','in_progress','submitted','under_review','changes_requested']).count(),
          'pending_reviews':Review.objects.filter(status__in=['scheduled','pending_human']).count(),'overdue_tasks':TaskAssignment.objects.filter(deadline__lt=timezone.now()).exclude(status__in=['approved','completed']).count(),'assignments':assignments,
          'projects':Project.objects.filter(is_active=True)}
        return render(request,'dashboard.html',context)
    if not profile or not profile.email_verified: return redirect('login')
    assignments=TaskAssignment.objects.filter(intern=profile).select_related('task','project').prefetch_related('submissions','reviews').order_by('-assigned_at')
    return render(request,'dashboard.html',{'is_admin':False,'profile':profile,'assignments':assignments,'latest_reviews':Review.objects.filter(assignment__intern=profile).order_by('-created_at')[:5]})

@login_required
@require_POST
def submit_task(request,task_id):
    profile=getattr(request.user,'profile',None)
    if not profile: return HttpResponseForbidden('Intern profile required')
    assignment=get_object_or_404(TaskAssignment,pk=task_id,intern=profile)
    if assignment.status in ['approved','completed']: messages.error(request,'This task is already approved and cannot be resubmitted.'); return redirect('dashboard')
    form=SubmissionForm(request.POST,request.FILES)
    if form.is_valid():
        latest=assignment.submissions.order_by('-version').first(); version=(latest.version+1) if latest else 1
        submission=form.save(commit=False); submission.assignment=assignment; submission.uploaded_by=request.user; submission.version=version; submission.save()
        assignment.status='submitted'; assignment.save(update_fields=['status'])
        AuditLog.objects.create(actor=request.user,action='submission_created',object_type='Submission',object_id=str(submission.pk),details={'assignment_id':assignment.pk,'version':version})
        queue_email(request.user.email,f'Submission received: {assignment.task.title}',f'Your version {version} submission was recorded at {timezone.localtime(submission.submitted_at)}.','submission:%s:%s'%(assignment.pk,version))
        # A review record is created unscheduled until Google Calendar has confirmed a real slot.
        if not assignment.reviews.filter(status__in=['scheduled','pending_human','in_progress']).exists(): schedule_review(assignment)
        messages.success(request,'Submission saved. A confirmation was generated through the configured email channel. Review scheduling is pending until a real calendar slot is confirmed.')
    else: messages.error(request,'Please correct the submission form: '+ '; '.join([f'{k}: {", ".join(v)}' for k,v in form.errors.items()]))
    return redirect('dashboard')

@login_required
@require_POST
def task_chat(request,task_id):
    profile=getattr(request.user,'profile',None)
    if not profile: return HttpResponseForbidden('Intern profile required')
    assignment=get_object_or_404(TaskAssignment,pk=task_id,intern=profile)
    question=request.POST.get('question','').strip()
    if not question or len(question)>4000: messages.error(request,'Enter a question up to 4,000 characters.'); return redirect('dashboard')
    conversation=ChatConversation.objects.filter(intern=profile,assignment=assignment).first()
    if not conversation: conversation=ChatConversation.objects.create(intern=profile,assignment=assignment)
    ChatMessage.objects.create(conversation=conversation,role='user',content=question)
    answer=answer_task_question(assignment,question)
    ChatMessage.objects.create(conversation=conversation,role='assistant',content=answer['answer'])
    messages.info(request,answer['answer'])
    return redirect('dashboard')

@login_required
@require_POST
def review_decision(request,review_id):
    profile=getattr(request.user,'profile',None)
    if not (request.user.is_superuser or (profile and profile.role in ['admin','mentor'])): return HttpResponseForbidden('Mentor or administrator access required')
    review=get_object_or_404(Review,pk=review_id)
    decision=request.POST.get('decision',''); reason=request.POST.get('reason','').strip()
    if decision in ['changes_requested','rejected'] and not reason: messages.error(request,'Provide an explanation for this decision.'); return redirect('dashboard')
    try:
        finalize_review(review,decision,request.user,reason)
        body = f"Review decision: {decision.replace('_',' ').title()}\n\n{reason or 'See the portal for details.'}"
        queue_email(review.assignment.intern.user.email, f'Review update: {review.assignment.task.title}', body, 'review:%s:%s' % (review.pk,decision))
        messages.success(request,'Review decision recorded and notification queued through the configured email channel.')
    except ValueError as exc: messages.error(request,str(exc))
    return redirect('dashboard')

def health(request): return HttpResponse('ok',content_type='text/plain')
