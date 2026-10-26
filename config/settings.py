import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-change-this-key-before-deployment')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = [x.strip() for x in os.getenv('DJANGO_ALLOWED_HOSTS','127.0.0.1,localhost').split(',') if x.strip()]
INSTALLED_APPS = [
 'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions',
 'django.contrib.messages','django.contrib.staticfiles','rest_framework','core',
]
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware',
 'django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware',
 'django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,
 'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASE_URL = os.getenv('DATABASE_URL','').strip()
if DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://'):
    import urllib.parse
    u=urllib.parse.urlparse(DATABASE_URL)
    DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':u.path.lstrip('/'),'USER':u.username,'PASSWORD':u.password,'HOST':u.hostname,'PORT':u.port or 5432,'CONN_MAX_AGE':60,'OPTIONS':{'sslmode':'require'} if os.getenv('DB_SSL','True').lower()=='true' else {}}}
else:
    DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE='en-us'
TIME_ZONE=os.getenv('DJANGO_TIME_ZONE','Asia/Kolkata')
USE_I18N=True
USE_TZ=True
STATIC_URL='static/'
STATICFILES_DIRS=[BASE_DIR/'static']
STATIC_ROOT=BASE_DIR/'staticfiles'
MEDIA_URL='/media/'
MEDIA_ROOT=BASE_DIR/'private_uploads'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='login'
LOGIN_REDIRECT_URL='dashboard'
LOGOUT_REDIRECT_URL='home'
EMAIL_MODE=os.getenv('EMAIL_MODE','console').lower()
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend' if EMAIL_MODE=='smtp' else 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST=os.getenv('EMAIL_HOST','smtp.gmail.com'); EMAIL_PORT=int(os.getenv('EMAIL_PORT','587'))
EMAIL_USE_TLS=os.getenv('EMAIL_USE_TLS','True').lower()=='true'; EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER',''); EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','no-reply@example.com')
MAX_UPLOAD_MB=int(os.getenv('MAX_UPLOAD_MB','10'))
AI_MODE=os.getenv('AI_MODE','mock').lower(); AI_API_KEY=os.getenv('AI_API_KEY',''); AI_MODEL=os.getenv('AI_MODEL','')
GOOGLE_INTEGRATION_MODE=os.getenv('GOOGLE_INTEGRATION_MODE','mock').lower()
CELERY_BROKER_URL=os.getenv('CELERY_BROKER_URL','redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND=os.getenv('CELERY_RESULT_BACKEND','redis://127.0.0.1:6379/1')
CELERY_TASK_ACKS_LATE=True
CELERY_TASK_REJECT_ON_WORKER_LOST=True
CELERY_TASK_DEFAULT_RETRY_DELAY=60
REST_FRAMEWORK={'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated'],'DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.UserRateThrottle'],'DEFAULT_THROTTLE_RATES':{'user':'120/hour'}}
if not DEBUG:
    SECURE_SSL_REDIRECT=True
    SESSION_COOKIE_SECURE=True
    CSRF_COOKIE_SECURE=True
    SECURE_HSTS_SECONDS=31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS=True
    SECURE_CONTENT_TYPE_NOSNIFF=True
    X_FRAME_OPTIONS='DENY'
