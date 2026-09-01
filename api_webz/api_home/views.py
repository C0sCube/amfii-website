from django.http import HttpResponse
from django.shortcuts import render

# def index(request):
#     return HttpResponse("Home Module")


def index(request):
    return render(request,'api_home/index.html')


def week(request):
    return render(request,'api_home/week.html')