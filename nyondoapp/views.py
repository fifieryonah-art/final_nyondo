from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import F
from .models import Stock, Product, Sale, Payment, DepositScheme, Supplier

# Create your views here.
def stockPage(request):
    products = Product.objects.all()
    total_products = products.count()
    low_stock_items = products.filter(stock_quantity__lt=F('reorder_level'))
    low_stock_count = low_stock_items.count()
    out_of_stock_count = products.filter(stock_quantity=0).count()
    for product in products:
        total_value += (product.stock_quantity * product.cost_price)

    context = {
        "total_products": total_products,
        "low_stock": low_stock_count,
        "out_of_stock": out_of_stock_count,
        
        "low_stock_items": low_stock_items,
        "products": products,
    }
    return render(request, 'stock.html', context)

def stock_list(request):
    stocks = Stock.objects.select_related("product", "supplier").order_by('id')
    return render(request,"stock/stock_list.html", {"stocks": stocks})

def add_stock(request):
     products = Product.objects.all()
     suppliers = Supplier.objects.all()

     if request.method == "POST":
        product_id = request.POST.get("product")
        supplier_id = request.POST.get("supplier")
        quantity = int(request.POST.get("quantity"))
        comments = request.POST.get("comments")
        total_cost = request.POST.get("total_cost")
        is_on_credit = bool(request.POST.get("is_on_credit"))
        is_paid = bool(request.POST.get("is_paid"))

        product = Product.objects.get(id=product_id)
        supplier = Supplier.objects.get(id=supplier_id)

        Stock.objects.create(
            product=product,
            supplier=supplier,
            quantity=quantity,
            comments=comments,
            total_cost=total_cost,
            is_on_credit=is_on_credit,
            is_paid=is_paid,
            entered_by=request.user
        )

        product.stock_quantity = F("stock_quantity") + quantity
        product.save()

        messages.success(request, "Stock added successfully!")
        return redirect("stock_list")
     
     context = {
        "products": products,
        "suppliers": suppliers 
     }

     return render(request, "add_stock.html", context)

def stock_delete(request, pk):
    stock = get_object_or_404(Stock,pk=pk)
    product = stock.product

    if request.method == "POST":

        # reduce inventory
        product.stock_quantity -= stock.quantity
        product.save()
        stock.delete()

        messages.success(request,"Stock deleted successfully")
        return redirect('stock_list')

    context = {
        'stock': stock
    }

    return render(request,'stock/delete_stock.html', context)

def stock_update(request, pk):
    stock = get_object_or_404( Stock, pk=pk)
    products = Product.objects.all()
    suppliers = Supplier.objects.all()
    old_quantity = stock.quantity

    if request.method == "POST":
        product_id = request.POST.get('product')
        supplier_id = request.POST.get('supplier')
        new_quantity = int(request.POST.get('quantity'))
        comments = request.POST.get('comments')
        total_cost = request.POST.get('total_cost')
        product = Product.objects.get(id=product_id)
        supplier = Supplier.objects.get(id=supplier_id)

        # calculate difference
        difference = (
            new_quantity - old_quantity
        )

        # update inventory
        product.stock_quantity += difference
        product.save()

        # update stock record
        stock.product = product
        stock.supplier = supplier
        stock.quantity = new_quantity
        stock.comments = comments
        stock.total_cost = total_cost
        stock.save()

        messages.success(request,"Stock updated successfully")

        return redirect('stock_list')

    context = {
        'stock': stock,
        'products': products,
        'suppliers': suppliers
    }

    return render(request,'stock/update_stock.html', context)

def admin_dashPage(request):
    return render(request, 'admin_dash.html')

def sales_dashPage(request):
     sales = Sale.objects.all()
     total_sales = sales.count()
     total_revenue = sum(s.amount for s in sales)
     recent_sales = sales.order_by('-date')[:10]

     context = {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "recent_sales": recent_sales,
     }
     return render(request, 'sales_dash.html', context)

def creditPage(request):
    return render(request, 'credit.html')

def loginPage(request):
    return render(request, 'login.html')

def indexPage(request):
    return render(request, 'index.html')


def payments_dashboard(request):
    payments = Payment.objects.all()
    total_payments = payments.count()
    total_collected = sum(p.total for p in payments)
    total_balance = sum(p.balance for p in payments)
    transport_fees = sum(p.transport_fee for p in payments)

    context = {
        "total_payments": total_payments,
        "total_collected": total_collected,
        "total_balance": total_balance,
        "transport_fees": transport_fees,
        "payments": payments,
    }
    return render(request, "payments_dashboard.html", context)

def deposit_dashboard(request):
    deposits = DepositScheme.objects.all()
    active_deposits = deposits.filter(is_completed=False)
    completed_deposits = deposits.filter(is_completed=True)

    context = {
        "total_deposits": deposits.count(),
        "active_deposits": active_deposits,
        "completed_deposits": completed_deposits,
    }
    return render(request, "deposit_dashboard.html", context)

