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
]

