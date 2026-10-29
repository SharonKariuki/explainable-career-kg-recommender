from django.urls import path

from core import views

urlpatterns = [
    path('auth/register/', views.register),
    path('auth/login/', views.login),
    path('auth/google/', views.google_login),
    path('auth/logout/', views.logout),
    path('auth/me/', views.me),
    path('auth/password/', views.change_password),
    path('profile/', views.profile),
    path('recommendations/', views.recommendations),
    path('recommendations/<str:career_code>/', views.recommendation_detail),
    path('careers/', views.careers),
    path('careers/<str:career_code>/', views.career_detail),
    path('saved/', views.saved_careers),
    path('saved/<str:career_code>/', views.saved_career),
    path('skills/', views.skills),
    path('progress/', views.progress),
]
