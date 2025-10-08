from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_complaint, name='upload_complaint'),
    path('process/', views.process_complaint, name='process_complaint'),
    # path('login/', views.login_view, name='login'),
    # path('signup/', views.signup_view, name='signup'),
    # path('upload/', views.handle_upload, name='upload'),
] 