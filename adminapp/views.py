from django.shortcuts import render
from datetime import datetime, date
from nyondoapp.models import Sale, Payment, Customer, Product
from django.db.models import Sum

# Create your views here.
def admin_dash(request):

    today = date.today()

    # SALES TODAY 
    sales_today = Sale.objects.filter(date=today)

    sales_total = sales_today.aggregate(total=Sum('final_amount'))['total'] or 0

    # REVENUE
    total_revenue = Payment.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0

    # CUSTOMERS
    customer_count = Customer.objects.count() or 0

    #PRODUCTS
    stock_count = Product.objects.count() or 0

    #LOW STOCK 
    low_stock = Product.objects.filter(stock_quantity__lte=10)
    low_stock_count = low_stock.count() or 0

    # CREDIT
    total_sales = Sale.objects.aggregate(total=Sum('final_amount'))['total'] or 0
    total_paid = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0

    total_credit = total_sales - total_paid
   
    recent_sales = Sale.objects.order_by('-date')[:5]

    recent_payments = Payment.objects.order_by('-id')[:5]

    top_products = ( Sale.objects.values('name__name')   
    .annotate(total_qty=Sum('quantity')).order_by('-total_qty')[:5]
     )
    
    low_stock_products = Product.objects.filter(stock_quantity__lte=5)

    context = {
        "sales_total": sales_total,
        "total_revenue": total_revenue,
        "customer_count": customer_count,
        "stock_count": stock_count,
        "low_stock_count": low_stock_count,
        "recent_sales": recent_sales,
        "recent_payments": recent_payments,
        "top_products": top_products,
        "total_credit": total_credit,
        "current_time": datetime.now(),
    }

    return render(request, "admin_dash.html", context)