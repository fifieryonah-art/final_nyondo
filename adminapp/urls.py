from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dash, name='admin_dash'),
    path('supplier_dashboard/', views.supplier_dashboard, name='supplier_dashboard'),
    path("create_employee/", views.create_employee, name="create_employee"),
    path("employees/", views.employee_list, name="employee_list"),
    path('employees/edit/<int:pk>/', views.edit_employee, name='edit_employee'),

    path('employees/status/<int:pk>/',views.toggle_employee_status,name='toggle_employee_status'),
    path('add_supplier/', views.add_supplier, name='add_supplier'),
    path('edit_supplier/<int:pk>/', views.edit_supplier, name='edit_supplier'),
    path('view_supplier/<int:pk>/', views.view_supplier, name='view_supplier'),
    path('delete_supplier<int:pk>/', views.delete_supplier, name='delete_supplier'),
    path('record_payment/<int:pk>/', views.record_payment, name='record_payment'),
    path('record_deposit/<int:pk>/', views.record_deposit, name='record_deposit'),
    path('deposit_dashboard/', views.deposit_dashboard, name='deposit_dashboard'),
    path('deposit_list/', views.deposit_list, name='deposit_list'),
    path('add_deposit/', views.add_deposit, name='add_deposit'),
    path('edit_deposit/<int:pk>/', views.edit_deposit, name='edit_deposit'),
    path('delete_deposit/<int:pk>/', views.delete_deposit, name='delete_deposit'),
    path('view_deposit/<int:pk>/', views.view_deposit, name='view_deposit'),
]