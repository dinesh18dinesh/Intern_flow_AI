from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from .models import InternProfile, Project, TaskTemplate, TaskAssignment, Submission, Review
from .services import allocate_next_task, finalize_review

class WorkflowTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user(username='intern@example.com',email='intern@example.com',password='LongPassword!123',first_name='Test')
  self.profile=InternProfile.objects.create(user=self.user,email_verified=True)
  self.project=Project.objects.create(name='Demo project')
  self.first=TaskTemplate.objects.create(project=self.project,title='Task 1',description='First task',sequence=1)
  self.second=TaskTemplate.objects.create(project=self.project,title='Task 2',description='Second task',sequence=2)
  from .models import ProjectMembership
  ProjectMembership.objects.create(project=self.project,intern=self.profile)
 def test_allocate_first_task_only_once(self):
  a=allocate_next_task(self.profile,self.project)
  self.assertEqual(a.task,self.first)
  self.assertIsNone(allocate_next_task(self.profile,self.project))
 def test_next_task_only_after_approval(self):
  a=allocate_next_task(self.profile,self.project)
  self.assertIsNone(allocate_next_task(self.profile,self.project))
  review=Review.objects.create(assignment=a,status='pending_human')
  finalize_review(review,'approved',self.user,'Looks good')
  self.assertTrue(TaskAssignment.objects.filter(intern=self.profile,task=self.second).exists())
 def test_submission_isolation(self):
  other=User.objects.create_user(username='other@example.com',email='other@example.com',password='LongPassword!123')
  other_profile=InternProfile.objects.create(user=other,email_verified=True)
  assignment=allocate_next_task(self.profile,self.project)
  client=Client(); client.force_login(other)
  response=client.post(f'/tasks/{assignment.pk}/submit/',{})
  self.assertEqual(response.status_code,404)
 def test_duplicate_email_registration(self):
  client=Client()
  response=client.post('/register/',{'full_name':'Duplicate','email':'INTERN@example.com','project_details':'Demo','skills':'Python','password':'LongPassword!123','confirm_password':'LongPassword!123'})
  self.assertEqual(response.status_code,200)
  self.assertEqual(User.objects.filter(email__iexact='intern@example.com').count(),1)
 def test_login_accepts_case_insensitive_email(self):
  client=Client()
  response=client.post('/login/',{'email':'INTERN@EXAMPLE.COM','password':'LongPassword!123'})
  self.assertRedirects(response,'/dashboard/')
  self.assertEqual(client.session['_auth_user_id'],str(self.user.pk))
  self.assertEqual(client.get('/dashboard/').status_code,200)
 def test_login_accepts_email_when_username_is_different(self):
  user=User.objects.create_user(username='mentor-login',email='mentor@example.com',password='LongPassword!123',is_staff=True)
  InternProfile.objects.create(user=user,role='mentor')
  client=Client()
  response=client.post('/login/',{'email':'mentor@example.com','password':'LongPassword!123'})
  self.assertRedirects(response,'/dashboard/')
  self.assertEqual(client.session['_auth_user_id'],str(user.pk))
 def test_unverified_intern_gets_verification_message(self):
  user=User.objects.create_user(username='pending@example.com',email='pending@example.com',password='LongPassword!123',is_active=False)
  InternProfile.objects.create(user=user)
  response=Client().post('/login/',{'email':'pending@example.com','password':'LongPassword!123'})
  self.assertContains(response,'Please verify your email before signing in.')
