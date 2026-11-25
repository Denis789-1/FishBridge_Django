from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
]

handler403 = 'main.views.handler403'
handler404 = 'main.views.handler404'
handler500 = 'main.views.handler500'