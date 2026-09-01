from django.urls import path
from .views import index

# api_bulk/urls.py

from django.urls import path
from .views import index

urlpatterns = [
    path('', index, name='bulk_home'),
]