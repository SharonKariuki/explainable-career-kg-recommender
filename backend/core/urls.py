from django.urls import path

from core import views

urlpatterns = [
    path('auth/register/', views.register),
    path('auth/login/', views.login),
    path('auth/logout/', views.logout),
    path('auth/me/', views.me),
    path('profile/', views.profile),
    path('recommendations/', views.recommendations),
    path('recommendations/<str:career_code>/', views.recommendation_detail),
]
