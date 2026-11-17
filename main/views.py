from django.shortcuts import render
from django.http import HttpResponse


def home(request):
    return render(request, 'main/index.html')


def placeholder(request):
    return HttpResponse("Эта страница будет добавлена позже.")