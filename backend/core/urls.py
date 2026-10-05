from django.urls import path

from core import views

urlpatterns = [
    path('auth/register/', views.register),
    path('auth/login/', views.login),
    path('auth/logout/', views.logout),
    path('auth/me/', views.me),
]
