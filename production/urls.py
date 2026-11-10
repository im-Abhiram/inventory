from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    path('', views.production_list, name='production_list'),
    path('create/', views.production_create, name='production_create'),
    path('<int:entry_id>/', views.production_detail, name='production_detail'),
    path('<int:entry_id>/edit/', views.production_edit, name='production_edit'),
]

