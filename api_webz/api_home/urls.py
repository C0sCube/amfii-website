from django.urls import path
from .views import index,week, login_view, logout_view

urlpatterns = [
    path('', login_view, name='login'),
    path("logout/", logout_view, name="logout"),
    path('home/', index, name='home'),
    path('week/', week, name = 'week')
]