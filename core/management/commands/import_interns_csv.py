import csv
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import InternProfile, Project, ProjectMembership

class Command(BaseCommand):
    help='Import intern identities from CSV columns: full_name,email,project,skills. Creates inactive accounts with unusable passwords; users must complete an administrator-defined invitation/verification flow.'
    def add_arguments(self, parser):
        parser.add_argument('csv_path')
    def handle(self, *args, **opts):
        try:
            fh=open(opts['csv_path'],newline='',encoding='utf-8-sig')
        except OSError as exc:
            raise CommandError(str(exc))
        created=0; skipped=0
        with fh:
            reader=csv.DictReader(fh)
            required={'full_name','email','project'}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise CommandError('CSV must contain headers: full_name,email,project (skills is optional).')
            for row in reader:
                email=(row.get('email') or '').strip().lower()
                name=(row.get('full_name') or '').strip()
                project_name=(row.get('project') or '').strip()
                if not email or not name or not project_name:
                    skipped+=1; continue
                if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
                    skipped+=1; continue
                project=Project.objects.filter(name=project_name).first()
                if not project:
                    skipped+=1; self.stderr.write(f'Skipped {email}: project not found: {project_name}'); continue
                user=User.objects.create_user(username=email,email=email,first_name=name[:150],is_active=False)
                user.set_unusable_password(); user.save()
                profile=InternProfile.objects.create(user=user,project_details=project_name,skills=(row.get('skills') or '').strip())
                ProjectMembership.objects.get_or_create(project=project,intern=profile)
                created+=1
        self.stdout.write(self.style.SUCCESS(f'Imported {created} inactive intern account(s); skipped {skipped}. No invitation email was sent. Add a secure invite/verification process before enabling these accounts.'))
