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
    # login urls
    path('', views.indexPage),
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logout_user, name='logout'),
    path('admin_dash/', include('adminapp.urls')),
    # stock urls
    path('stock/', views.stockPage, name='stock'),
    path('stock_list/', views.stock_list, name='stock_list'),
    path('stock_records/', views.stock_records, name='stock_records'),
    path('add_stock/', views.add_stock, name='add_stock'),
    path('stock/update/<int:pk>/', views.stock_update, name='stock_update'),
    path('stock/delete/<int:pk>/', views.stock_delete, name='stock_delete'),
    path('stock_report/', views.stock_report, name='stock_report'),
    path('stock/suppliers/', views.stock_supplier_dashboard, name='stock_supplier_dashboard'),
      path('low_stock_items/',views.low_stock_items,name='low_stock_items'),
    #product urls
    path('add_product/', views.add_product, name='add_product'),
    path('product_list/', views.product_list, name='product_list'),
    path('product/update/<int:pk>/', views.update_product, name='update_product'),
    path('delete_product/<int:pk>/', views.delete_product, name='delete_product'),
   # sales urls 
    path('employee_dash/', views.employee_dash, name='employee_dash'),
    path('sales_dash/', views.sales_dash, name='sales_dash'),
    path('sales_list/', views.sales_list, name='sales_list'),
    path('add_sales/', views.add_sales, name='add_sales'),
    # deposit scheme urls
    path('credit/', views.creditPage, name='credit'),
    path('add_customer/', views.add_customer, name='add_customer'),
    path('customer_list/', views.customer_list, name='customer_list'),
    path('customers/edit/<int:pk>/', views.customer_edit, name='customer_edit'),
    path('customers/delete/<int:pk>/', views.delete_customer, name='delete_customer'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    # payment urls
    path('payments/add/', views.add_payment, name='add_payment'),
    path('payments/', views.payment_list, name='payment_list'), 
   
]
