from django.urls import path
from . import views

urlpatterns = [
    path('directions/', views.calculate_route, name='calculate_route'),
]