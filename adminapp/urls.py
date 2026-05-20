from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dash, name='admin_dash'),
    path('supplier_dashboard/', views.supplier_dashboard, name='supplier_dashboard'),
    path('add_supplier/', views.add_supplier, name='add_supplier'),
    path('edit_supplier/<int:pk>/', views.edit_supplier, name='edit_supplier'),
    path('view_supplier/<int:pk>/', views.view_supplier, name='view_supplier'),
    path('delete_supplier<int:pk>/', views.delete_supplier, name='delete_supplier'),
    path('record_payment/<int:pk>/', views.record_payment, name='record_payment'),
    path('record_deposit/', views.record_deposit, name='record_deposit'),
    path('deposit_dashboard/', views.deposit_dashboard, name='deposit_dashboard'),
    path('deposit_list/', views.deposit_list, name='deposit_list'),
]