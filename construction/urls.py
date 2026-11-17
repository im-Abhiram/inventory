from django.urls import path
from . import views

app_name = 'construction'

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('<int:project_id>/', views.project_detail, name='project_detail'),
    path('<int:project_id>/edit/', views.project_edit, name='project_edit'),
    path('<int:project_id>/daily-entry/create/', views.daily_entry_create, name='daily_entry_create'),
    path('daily-entry/<int:entry_id>/', views.daily_entry_detail, name='daily_entry_detail'),
    # Site Product Pricing
    path('<int:project_id>/pricing/update/', views.project_price_update, name='project_price_update'),
    path('<int:project_id>/pricing/bulk-update/', views.project_prices_bulk_update, name='project_prices_bulk_update'),
    path('<int:project_id>/pricing/<int:product_id>/delete/', views.project_price_delete, name='project_price_delete'),
    path('<int:project_id>/pricing/json/', views.project_prices_json, name='project_prices_json'),
]

