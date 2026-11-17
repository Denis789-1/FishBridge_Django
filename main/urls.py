from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('ponds/', views.placeholder, name='ponds'),
    path('pond/', views.placeholder, name='pond'),
    path('login/', views.placeholder, name='login'),
    path('register/', views.placeholder, name='register'),
    path('account/', views.placeholder, name='account'),
]