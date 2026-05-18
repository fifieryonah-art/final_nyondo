from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import F
from .models import Stock, Product, Sale, Payment, DepositScheme, Supplier
from decimal import Decimal
from .forms import SupplierForm
from django.db.models import Sum
#from django.contrib.auth.decorators import login_required

# Create your views here.
def loginPage(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect("admin_dash")

        else:

            messages.error(
                request,
                "Invalid username or password"
            )

    return render(request, "login.html")

def stockPage(request):
    products = Product.objects.all()
    total_products = products.count()
    low_stock_items = products.filter(stock_quantity__lt=F('reorder_level'))
    low_stock_count = low_stock_items.count()
    out_of_stock_count = products.filter(stock_quantity=0).count()
    total_value = 0
    for product in products:
        total_value += (product.stock_quantity * product.cost_price)

    context = {
        "total_products": total_products,
        "low_stock": low_stock_count,
        "out_of_stock": out_of_stock_count,
        "total_value": total_value,
        "low_stock_items": low_stock_items,
        "products": products,
    }
    return render(request, 'stock.html', context)

def stock_list(request):
    stocks = Stock.objects.select_related("product", "supplier").order_by('id')
    return render(request,"stock_list.html", {"stocks": stocks})

def add_stock(request):
     products = Product.objects.all()
     suppliers = Supplier.objects.all()

     if request.method == "POST":
        product_id = request.POST.get("product")
        supplier_id = request.POST.get("supplier")
        cost_price = int(request.POST.get("cost_price"))
        quantity = int(request.POST.get("quantity"))
        comments = request.POST.get("comments")
        is_on_credit = "is_on_credit" in request.POST 
        is_paid = "is_paid" in request.POST

        # auto calculate total cost
        total_cost = cost_price * quantity

        #checkboxes
        cost_price = float(request.POST.get("cost_price"))
        unit_price = float(request.POST.get("unit_price"))

        product = Product.objects.get(id=product_id)
        supplier = Supplier.objects.get(id=supplier_id)

        # update product prices and stock quantity
        product.cost_price = cost_price
        product.unit_price = unit_price
        product.stock_quantity += quantity
        product.save()

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


def admin_dash(request):
    return render(request, 'admin_dash.html')


def employee_dash(request):
     sales = Sale.objects.all()
     total_sales = sales.count()
     product = Product.objects.all()
     total_revenue = sum(s.amount for s in sales)
     recent_sales = sales.order_by('-date')[:10]

     context = {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "recent_sales": recent_sales,
        "products": product
     }
     return render(request, 'employee_dash.html', context)

def creditPage(request):
    return render(request, 'credit.html')


def indexPage(request):
    return render(request, 'index.html')


def add_product(request):

    if request.method == 'POST':

        name = request.POST.get('name')
        description = request.POST.get('description')
        specification = request.POST.get('specification')
        stock_quantity = request.POST.get('stock_quantity')
        type = request.POST.get('type')
        cost_price =Decimal(request.POST.get('cost_price'))
        unit_price = Decimal(request.POST.get('unit_price'))
        reorder_level = request.POST.get('reorder_level') or 10


        Product.objects.create(

            name=name,
            description=description,
            specification=specification,
            stock_quantity=stock_quantity,
            type=type,
            cost_price=cost_price,
            unit_price=unit_price,
            reorder_level=reorder_level,
            entered_by=request.user
        )

        return redirect('product_list')

    return render(request, 'add_product.html')

def product_list(request):
    products = Product.objects.all()

    context = {
        'products': products
    }

    return render(request, 'product_list.html', context)

def update_product(request, pk):
    product = get_object_or_404( Product, pk=pk)

    if request.method == "POST":
       product.name = request.POST.get("name")
       product.stock_quantity = int(request.POST.get("quantity"))
       product.cost_price = float(request.POST.get("cost_price"))
       product.unit_price = float(request.POST.get("unit_price"))
       product.comments = request.POST.get("comments")
       product.profit_margin = request.POST.get("profit")
       product.entered_by = request.user
       

       messages.success(request,"Product updated successfully")
       return redirect("product_list")

    context ={
        'product': product
    }

    return render(request, 'update_product.html', context)

def delete_product(request):
    return render(request, 'delete_product.html')


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

def add_supplier(request):
    if request.method=="POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("supplier")

    else:
        form = SupplierForm()

    context ={
        "form": form
    }


    return render(request, "add_supplier.html", context )

def supplier(request):
    suppliers = Supplier.objects.all()

    total_suppliers = suppliers.count()
    pending_credit = suppliers.filter(status='pending').count()

    context = {
    'suppliers': suppliers,
    'total_suppliers': total_suppliers,
    'pending_credit': pending_credit,
     }

    return render(request, "supplier.html", context)

def sales_dash(request):
    products = Product.objects.all()
    sales = Sale.objects.all().order_by('-date')

    total_products = products.count()
    total_sales = sales.count()

    total_revenue = 0
    for sale in sales:
        total_revenue += sale.total_price

    total_items_sold = sales.aggregate(
        Sum('quantity'))['quantity__sum'] or 0
    

    transport_total = sales.aggregate(
        Sum('transport')
    )['transport__sum'] or 0
    

    low_stock = Product.objects.filter(stock_quantity__lt=10)

    low_stock_count = low_stock.count()

    top_selling_items = Sale.objects.all().order_by('-quantity')[:5]

    supplier_credit = 0
    deposits = 0

    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_items_sold': total_items_sold,
        'transport_total': transport_total,
        'supplier_credit': supplier_credit,
        'deposits': deposits,
        'low_stock': low_stock,
        'low_stock_count': low_stock_count,
        'top_selling_items': top_selling_items,
            }
    return render(request, "sales_dash.html", context)

def sales_list(request):
    sales = Sale.objects.all().order_by('-date')
    context = {
        'sales': sales
    }
    return render(request, 'sales_list.html', context)

def add_sales(request):
    
    return render(request, 'add_sales.html')