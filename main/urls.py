
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('ponds/', views.ponds_list, name='ponds'),
    path('api/ponds/', views.ponds_api, name='ponds_api'),
    path('ponds/<int:pk>/', views.pond_detail, name='pond_detail'),
    path('booking/', views.booking, name='booking'),
    path('booking/<int:booking_id>/rentals/', views.rental_add, name='rental_add'),
    path('ranger/catch/', views.ranger_catch, name='ranger_catch'),
    path('ichthyologist/', views.ichthyologist_dashboard, name='ichthyologist_dashboard'),
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('account/', views.account, name='account'),
    path('about/', views.about, name='about'),
    path('search/', views.search_results, name='search'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('logout/', views.logout_page, name='logout'),
]
