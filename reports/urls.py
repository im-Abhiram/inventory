from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_index, name='reports_index'),
    path('inventory/', views.inventory_report, name='inventory_report'),
    path('stock-movement/', views.stock_movement_report, name='stock_movement_report'),
    path('production/', views.production_report, name='production_report'),
    path('financial-summary/', views.financial_summary_report, name='financial_summary_report'),
    path('credit/', views.client_credit_report, name='credit_report'),
    path('construction/', views.construction_report, name='construction_report'),
    path('dispatch/', views.dispatch_report, name='dispatch_report'),
]

