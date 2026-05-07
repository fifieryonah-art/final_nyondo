from django.shortcuts import render

# Create your views here.
def stockPage(request):
    return render(request, 'stock.html')

def admin_dashPage(request):
    return render(request, 'admin_dash.html')

def sales_dashPage(request):
    return render(request, 'sales_dash.html')
