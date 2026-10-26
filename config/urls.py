from django.contrib import admin
from django.urls import path
from core import views
urlpatterns = [
 path('admin/', admin.site.urls), path('', views.home, name='home'),
 path('register/', views.register, name='register'), path('verify/<uidb64>/<token>/', views.verify_email, name='verify_email'),
 path('login/', views.login_view, name='login'), path('logout/', views.logout_view, name='logout'),
 path('dashboard/', views.dashboard, name='dashboard'), path('tasks/<int:task_id>/submit/', views.submit_task, name='submit_task'),
 path('tasks/<int:task_id>/chat/', views.task_chat, name='task_chat'), path('reviews/<int:review_id>/decision/', views.review_decision, name='review_decision'),
 path('health/', views.health, name='health'),
]
