from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    path('payments/<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('payments/<int:payment_id>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('credit/', views.credit_management, name='credit_management'),
    path('credit/<int:client_id>/update-limit/', views.update_credit_limit, name='update_credit_limit'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/categories/', views.expense_category_list, name='expense_category_list'),
]

