from django.urls import path
from .views import index,week

urlpatterns = [
    path('', index, name='home'),
    path('week/', week, name = 'week')
]