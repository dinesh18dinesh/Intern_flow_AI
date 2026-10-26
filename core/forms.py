from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from .models import Submission

class RegistrationForm(forms.Form):
    full_name=forms.CharField(max_length=150)
    email=forms.EmailField()
    project_details=forms.CharField(max_length=240)
    skills=forms.CharField(widget=forms.Textarea(attrs={'rows':3}),required=False)
    password=forms.CharField(widget=forms.PasswordInput,min_length=10)
    confirm_password=forms.CharField(widget=forms.PasswordInput)
    def clean_email(self):
        email=self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email
    def clean(self):
        data=super().clean()
        if data.get('password') and data.get('confirm_password') and data['password']!=data['confirm_password']:
            self.add_error('confirm_password','Passwords do not match.')
        return data

class SubmissionForm(forms.ModelForm):
    class Meta:
        model=Submission
        fields=['file','repository_url','deployed_url','explanation']
        widgets={'explanation':forms.Textarea(attrs={'rows':4,'placeholder':'Explain your approach, testing, and known limitations...'})}
    def clean_file(self):
        f=self.cleaned_data.get('file')
        if f:
            if f.size > settings.MAX_UPLOAD_MB*1024*1024: raise forms.ValidationError(f'File must be {settings.MAX_UPLOAD_MB} MB or smaller.')
            allowed={'.pdf','.docx','.zip','.py','.js','.ts','.html','.css','.txt','.md','.png','.jpg','.jpeg','.webp','.csv','.json'}
            import os
            if os.path.splitext(f.name)[1].lower() not in allowed: raise forms.ValidationError('This file type is not allowed.')
        return f
