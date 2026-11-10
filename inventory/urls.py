from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_list, name='inventory_list'),
    path('adjust/', views.inventory_adjust, name='inventory_adjust'),
    path('transactions/', views.stock_transactions, name='stock_transactions'),
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/create/', views.purchase_create, name='purchase_create'),
    path('purchases/<int:purchase_id>/', views.purchase_detail, name='purchase_detail'),
]

