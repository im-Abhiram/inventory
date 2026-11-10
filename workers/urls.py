from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('', views.worker_list, name='worker_list'),
    path('create/', views.worker_create, name='worker_create'),
    path('<int:worker_id>/edit/', views.worker_edit, name='worker_edit'),
    path('<int:worker_id>/toggle-status/', views.worker_toggle_status, name='worker_toggle_status'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/record/', views.attendance_record, name='attendance_record'),
]

