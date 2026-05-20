import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import F
from .models import Stock, Product, Sale, Payment, Customer
from decimal import Decimal
from .forms import CustomerForm
from adminapp.models import Supplier

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





def employee_dash(request):
     sales = Sale.objects.all()
     total_sales = sales.count()
     product = Product.objects.all()
     total_revenue = sum(p.amount_paid for p in Payment.objects.all())
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



def sales_dash(request):
    products = Product.objects.all()
    sales = Sale.objects.all().order_by('-date')

    total_products = products.count()
    total_sales = sales.count()

    total_revenue = 0
    for sale in sales:
        total_revenue += sale.final_amount

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
    products = Product.objects.all()
    customers = Customer.objects.all()

    if request.method == 'POST':
        #get form data
        receipt_number = f"SALE-{uuid.uuid4().hex[:6].upper()}"
        product_id = request.POST.get('product')
        customer_id = request.POST.get('customer_name')
        quantity = int(request.POST.get('quantity'))
        distance = int(request.POST.get('distance'))
        payment_method = request.POST.get('payment_method')
        comments = request.POST.get('comments')

        #fetch related objects
        product = Product.objects.get(id=product_id)
        customer = Customer.objects.get(id=customer_id)

        #subtotal
        sub_total = quantity * product.unit_price

        #Transport 
        if distance <= 10 and sub_total >= 500000:
            transport_fee = 0
        else:
            transport_fee = 30000
        final_amount = sub_total + transport_fee

        sale = Sale(
            name=product,
            quantity=quantity,
            distance=distance,
            unit_price=product.unit_price,
            transport=transport_fee,
            sub_total=sub_total,
            final_amount=final_amount,
            customer_name=customer,
            payment_method=payment_method,
            comments=comments,
            recorded_by=request.user,
            receipt_number=receipt_number,
         )
        sale.save()
        context = {
            'sale': sale,
            'distance': distance,
            'total': final_amount
        }
        return redirect('add_payment')
    context={
        'products': products,
        'customers': customers,
        'payment_methods': Sale.PAYMENT_METHODS,
    }
    
    return render(request, 'add_sales.html', context)

def add_customer(request, pk=None):
    form = CustomerForm()
    if request.method =='POST':
        form = CustomerForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('customer_list')
        else:
            form = CustomerForm()

    context = {
            'form': form,
          }
    return render(request, 'add_customer.html', context)

def customer_list(request):
    customers = Customer.objects.all()
    context = {
    'customers': customers,
    'total_customers': customers.count(),
    'on_scheme': customers.filter(on_scheme=True).count(),
    'normal_customers': customers.filter(on_scheme=False).count(),
     }
    return render(request, 'customer_list.html', context)

def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        form = CustomerForm(request.POST, instanc=customer)
        if form.is_valid():
            form.save()
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'add_customer.html', {'form': form})

def delete_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        customer.delete()
        return redirect('customer_list')
    return render(request, 'delete_customer.html', {'customer': customer})

def add_payment(request):

    customers = Customer.objects.all()

    sales = Sale.objects.all()

    receipt_number = f"RCPT-{uuid.uuid4().hex[:6].upper()}"

    if request.method == "POST":

        customer_id = request.POST.get('customer')

        sale_id = request.POST.get('sale')

        total = float(request.POST.get('total'))

        amount_paid = float(request.POST.get('amount_paid'))

        payment_method = request.POST.get('payment_method')

        receipt_number = request.POST.get('receipt_number')

        # related objects
        customer = Customer.objects.get(id=customer_id)

        sale = Sale.objects.get(id=sale_id)

        # balance calculation
        balance = total - amount_paid

        # create payment
        payment = Payment.objects.create(

            order_id=sale,

            customer=customer,

            total=total,

            amount_paid=amount_paid,

            balance=balance,

            payment_method=payment_method,

            receipt_number=receipt_number,

            entered_by=request.user
        )

        context = {

            'payment': payment,

            'balance': balance,

            'amount_paid': amount_paid,

            'total': total,
        }


        return render(request, 'receipt.html', context)

    context = {

        'customers': customers,

        'sales': sales,

        'payment_methods': Payment.PAYMENT_METHODS,

        'receipt_number': receipt_number,
    }

    return render(request, 'add_payment.html', context)


def payment_list(request):

    payments = Payment.objects.all().order_by('-created_at')

    total_payments = payments.count()

    total_paid = 0

    total_balance = 0

    for payment in payments:

        total_paid += payment.amount_paid

        total_balance += payment.balance

    context = {

        'payments': payments,

        'total_payments': total_payments,

        'total_paid': total_paid,

        'total_balance': total_balance,
    }

    return render(request, 'payment_list.html', context)

def customer_detail(request, pk):

    customer = Customer.objects.get(id=pk)

    sales = Sale.objects.filter(customer_name=customer)

    payments = Payment.objects.filter(customer=customer)

    total_sales = sum(sale.final_amount for sale in sales)

    total_paid = sum(payment.amount_paid for payment in payments)

    balance = total_sales - total_paid

    context = {

        'customer': customer,
        'sales': sales,
        'payments': payments,
        'total_sales': total_sales,
        'total_paid': total_paid,
        'balance': balance,
    }

    return render(request, 'customer_detail.html', context)