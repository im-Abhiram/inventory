from django.urls import path
from . import views

app_name = 'dispatch'

urlpatterns = [
    path('', views.dispatch_list, name='dispatch_list'),
    path('create/', views.dispatch_create, name='dispatch_create'),
    path('<int:dispatch_id>/', views.dispatch_detail, name='dispatch_detail'),
    path('<int:dispatch_id>/receipt/', views.dispatch_receipt, name='dispatch_receipt'),
]

