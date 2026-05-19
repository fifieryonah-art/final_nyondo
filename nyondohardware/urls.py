"""
URL configuration for nyondohardware project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from nyondoapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.indexPage),
    path('stock/', views.stockPage, name='stock'),
    path('employee_dash/', views.employee_dash, name='employee_dash'),
    path('credit/', views.creditPage, name='credit'),
    path('login/', views.loginPage, name="login"),
    path('stock_list/', views.stock_list, name='stock_list'),
    path('add_stock/', views.add_stock, name='add_stock'),
    path('stock/update/<int:pk>/', views.stock_update, name='stock_update'),
    path('stock/delete/<int:pk>/', views.stock_delete, name='stock_delete'),
    path('add_product/', views.add_product, name='add_product'),
    path('product_list/', views.product_list, name='product_list'),
    path('supplier/', views.supplier, name="supplier"),
    path('product/update/<int:pk>/', views.update_product, name='update_product'),
    path('add_supplier/', views.add_supplier, name='add_supplier'),
    path('sales_dash/', views.sales_dash, name='sales_dash'),
    path('sales_list/', views.sales_list, name='sales_list'),
    path('add_sales/', views.add_sales, name='add_sales'),
    path('add_customer/', views.add_customer, name='add_customer'),
    path('customer_list/', views.customer_list, name='customer_list'),
    path('customers/edit/<int:pk>/', views.add_customer, name='customer_edit'),
    path('customers/delete/<int:pk>/', views.delete_customer, name='delete_customer'),
    path('payments/add/', views.add_payment, name='add_payment'),
    path('payments/', views.payment_list, name='payment_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('admin_dash/', include('adminapp.urls')),
]
