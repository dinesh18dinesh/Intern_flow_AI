import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import InternProfile,Project,ProjectMembership,TaskTemplate
class Command(BaseCommand):
 help='Create a demo project, task sequence, and optionally 100 demo interns.'
 def add_arguments(self,parser): parser.add_argument('--interns',type=int,default=100)
 def handle(self,*args,**opts):
  project,_=Project.objects.get_or_create(name='AI Web Development Internship',defaults={'description':'Sample project for task allocation and reviews.'})
  task_data=[('Environment setup and Git workflow','Set up your development environment, create a repository, and document the steps.',1,3),('Build a CRUD feature','Implement a validated CRUD feature with tests and documentation.',2,5),('Testing and deployment report','Add automated tests, document deployment, and describe security considerations.',3,7)]
  for title,desc,seq,days in task_data: TaskTemplate.objects.get_or_create(project=project,sequence=seq,defaults={'title':title,'description':desc,'instructions':'Read the brief carefully. Commit your work and explain design decisions.','deliverables':'Repository URL, setup instructions, tests, and a short report.','deadline_days':days,'evaluation_criteria':[{'name':'Correctness','weight':40},{'name':'Code quality','weight':25},{'name':'Testing','weight':20},{'name':'Documentation','weight':15}]})
  demo_email=os.getenv('DEMO_LOGIN_EMAIL','internflow.demo@example.test').strip().lower()
  demo_password=os.getenv('DEMO_LOGIN_PASSWORD','DemoPass!12345')
  for i in range(1,opts['interns']+1):
   email=demo_email if i==1 else f'demo.intern{i:03d}@example.test'
   user,created=User.objects.get_or_create(username=email,defaults={'email':email,'first_name':f'Demo Intern {i:03d}','is_active':True})
   if i==1:
    user.email=email; user.first_name='InternFlow Demo'; user.is_active=True; user.set_password(demo_password); user.save()
   elif created: user.set_password(demo_password); user.save()
   profile,_=InternProfile.objects.get_or_create(user=user,defaults={'email_verified':True,'project_details':project.name,'skills':'Python, HTML, CSS'})
   if not profile.email_verified: profile.email_verified=True; profile.save()
   ProjectMembership.objects.get_or_create(project=project,intern=profile)
  self.stdout.write(self.style.SUCCESS(f'Demo data ready: {project.name}; {opts["interns"]} demo interns. Demo login email: {demo_email}; password is configured in DEMO_LOGIN_PASSWORD.'))
