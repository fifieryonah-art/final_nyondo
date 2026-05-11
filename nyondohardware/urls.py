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
from django.urls import path
from nyondoapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.indexPage),
    path('stock/', views.stockPage, name='stock'),
    path('admin_dash/', views.admin_dash, name='admin_dash'),
    path('sales_dash/', views.sales_dash, name='sales_dash'),
    path('credit/', views.creditPage, name='credit'),
    path('login/', views.loginPage, name="login"),
    path('stock_list/', views.stock_list, name='stock_list'),
    path('add_stock/', views.add_stock, name='add_stock'),
    path('stock/update/<int:pk>/', views.stock_update, name='stock_update'),
    path('stock/delete/<int:pk>/', views.stock_delete, name='stock_delete'),
    path('add_product/', views.add_product, name='add_product'),
    path('product_list/', views.product_list, name='product_list'),
]
