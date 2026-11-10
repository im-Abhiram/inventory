from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from accounts.dashboard_views import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('dashboard'), name='root'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('inventory/', include('inventory.urls')),
    path('production/', include('production.urls')),
    path('clients/', include('clients.urls')),
    path('dispatch/', include('dispatch.urls')),
    path('construction/', include('construction.urls')),
    path('finance/', include('finance.urls')),
    path('workers/', include('workers.urls')),
    path('reports/', include('reports.urls')),
]
