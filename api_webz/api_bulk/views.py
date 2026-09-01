# api_bulk/views.py

from django.shortcuts import render

def index(request):
    return render(request, 'api_bulk/index.html')