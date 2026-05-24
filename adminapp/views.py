from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, date
from decimal import Decimal
from nyondoapp.models import Sale, Payment, Customer, Product, Stock
from django.db.models import Sum, Max, F
from .forms import SupplierForm, SupplierPaymentForm
from .models import Supplier, DepositScheme, DepositPayment
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from nyondoapp.models import Employee
from .forms import EmployeeCreationForm


# Create your views here.
def admin_dash(request):
    today = date.today()
    sales_today = Sale.objects.filter(date=today)
    sales_total = sales_today.aggregate(total=Sum('final_amount'))['total'] or 0
    total_revenue = Payment.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    customer_count = Customer.objects.count() or 0
    stock_count = Product.objects.count() or 0
    low_stock = Product.objects.filter(stock_quantity__lte=10)
    low_stock_count = low_stock.count() or 0
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




def create_employee(request):

    if request.method == "POST":
        form = EmployeeCreationForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Employee created successfully!")
            return redirect("employee_list")

    else:
        form = EmployeeCreationForm()

    return render(request, "create_employee.html", {"form": form})


# employee list page

def employee_list(request):
    employees = Employee.objects.all().order_by("-id")

    return render(request, "employee_list.html", {
        "employees": employees
    })


def edit_employee(request, pk):

    employee = get_object_or_404(Employee, pk=pk)
    user = employee.user

    if request.method == "POST":

        # Employee fields
        employee.employee_id = request.POST.get("employee_id")
        employee.role = request.POST.get("role")
        employee.gender = request.POST.get("gender")

        # User fields
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")

        # Password only if filled
        password = request.POST.get("password")
        if password:
            user.set_password(password)

        user.save()
        employee.save()

        messages.success(request, "Employee updated successfully")
        return redirect("employee_list")

    return render(request, "edit_employee.html", {
        "employee": employee
    })

def toggle_employee_status(request, pk):

    employee = get_object_or_404(Employee, pk=pk)

    user = employee.user

    user.is_active = not user.is_active

    user.save()

    return redirect('employee_list')


def add_supplier(request):

    if request.method == "POST":
        form = SupplierForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("supplier_dashboard")

    else:
        form = SupplierForm()

    context = {
        "form": form
    }

    return render(request, "add_supplier.html", context)



def supplier_dashboard(request):
    suppliers = Supplier.objects.all()
    total_suppliers = suppliers.count()
    pending_credit = suppliers.filter(status='pending').count()
    total_credit = suppliers.aggregate(total=Sum('outstanding_credit')
    )['total'] or 0

    context = {
        'suppliers': suppliers,
        'total_suppliers': total_suppliers,
        'pending_credit': pending_credit,
        'total_credit': total_credit,
    }

    return render(request, "supplier_dashboard.html", context)


def edit_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == "POST":
        form = SupplierForm(request.POST,instance=supplier)
        if form.is_valid():
            form.save()
            return redirect('supplier_dashboard')
    else:
        form = SupplierForm(instance=supplier)

    context = {
        'form': form
    }

    return render( request,'edit_supplier.html',context)

def view_supplier(request, pk):

    supplier = get_object_or_404(Supplier,pk=pk)

    context = {
        'supplier': supplier
    }

    return render(request,'view_supplier.html', context)

def delete_supplier(request, pk):

    supplier = get_object_or_404(Supplier,pk=pk)
    if request.method == "POST":
        supplier.delete()

        return redirect(
            'supplier_dashboard'
        )

    context = {
        'supplier': supplier
    }

    return render(request,'delete_supplier.html',context)

def record_payment(request, pk):

    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == "POST":

        form = SupplierPaymentForm(request.POST)

        if form.is_valid():

            payment = form.save(commit=False)
            payment.supplier = supplier
            payment.save()

            # update supplier totals
            supplier.amount_paid += payment.amount_paid

            supplier.outstanding_credit = (
                supplier.total_amount - supplier.amount_paid
            )

            # update status
            if supplier.outstanding_credit <= 0:
                supplier.status = "Paid"

            elif supplier.amount_paid > 0:
                supplier.status = "Partial"

            else:
                supplier.status = "Pending"

            supplier.save()

            return redirect('view_supplier', pk=supplier.id)

    else:
        form = SupplierPaymentForm()

    return render(request, 'record_payment.html', {
        'form': form,
        'supplier': supplier
    })


def deposit_dashboard(request):

    deposits = DepositScheme.objects.all()

    active = 0
    completed = 0

    total_paid_all = 0
    total_balance_all = 0

    for d in deposits:

        paid = DepositPayment.objects.filter(scheme=d).aggregate(
            total=Sum("amount_paid")
        )["total"] or 0

        balance = (d.total_amount or 0) - paid

        # attach runtime values (NOT DB)
        d.paid = paid
        d.balance = balance

        # STATUS LOGIC (LIVE)
        if paid == 0:
            d.status = "Pending"
        elif balance <= 0:
            d.status = "Completed"
            completed += 1
        else:
            d.status = "Active"
            active += 1

        total_paid_all += paid
        total_balance_all += balance

    context = {
        "deposits": deposits,

        "active_schemes": active,
        "completed_schemes": completed,

        "total_paid": total_paid_all,
        "total_balance": total_balance_all,
    }

    return render(request, "deposit_dashboard.html", context)
def deposit_list(request):

    deposits = DepositScheme.objects.all()
    deposit_rows = []

    for deposit in deposits:

        payments = deposit.payments.all()  

        last_payment = payments.aggregate(
            last=Max("payment_date")
        )["last"]

        total_paid = payments.aggregate(
            total=Sum("amount_paid")
        )["total"] or 0

        # status logic (safe version)
        if hasattr(deposit, "balance") and deposit.balance is not None:
            status = "Completed" if deposit.balance <= 0 else "Active"
        else:
            status = "Active"

        deposit_rows.append({
            "deposit": deposit,
            "last_payment": last_payment,
            "total_paid": total_paid,
            "status": status,
        })

    return render(request, "deposit_list.html", {
        "deposit_rows": deposit_rows
    })


def add_deposit(request):

    customers = Customer.objects.all()
    products = Product.objects.all()

    if request.method == "POST":

        customer_id = request.POST.get("customer")
        product_id = request.POST.get("product")
        quantity = request.POST.get("quantity_expected")
        amount_paid = request.POST.get("amount_paid")

        customer = Customer.objects.get(id=customer_id)
        product = Product.objects.get(id=product_id)

        quantity_value = int(quantity or 0)
        amount_paid_value = Decimal(amount_paid or 0)
        total_amount = (product.unit_price * Decimal(quantity_value))
        balance = total_amount - amount_paid_value
        status = 'Completed' if balance <= 0 else 'Active'

        DepositScheme.objects.create(
            customer=customer,
            product=product,
            total_amount=total_amount,
            quantity_expected=quantity_value,
            amount_paid=amount_paid_value,
            balance=balance,
            status=status,
        )

        return redirect('deposit_dashboard')

    return render(request, "add_deposit.html", {
        "customers": customers,
        "products": products
    })

def record_deposit(request, pk):
    scheme = get_object_or_404(DepositScheme, id=pk)

    if request.method == "POST":
        amount = request.POST.get("amount_paid")
        method = request.POST.get("payment_method")
        comment = request.POST.get("comment")

        if amount:
            amount = float(amount)

            DepositPayment.objects.create(
                scheme=scheme,
                amount_paid=amount,
                payment_method=method,
                comment=comment,
                received_by=request.user
            )

            # update scheme
            scheme.amount_paid = (scheme.amount_paid or 0) + amount
            scheme.balance = scheme.total_amount - scheme.amount_paid

            if scheme.balance <= 0:
                scheme.status = "Completed"
            else:
                scheme.status = "Active"

            scheme.save()

        return redirect('deposit_dashboard')

    return render(request, "record_deposit.html", {
        "scheme": scheme
    })

def edit_deposit(request, pk):
    deposit = get_object_or_404(DepositScheme, id=pk)
    if request.method == "POST":
        deposit.quantity_expected = request.POST.get("quantity_expected")
        deposit.save()
        return redirect("deposit_list")
    
    return render(request, "edit_deposit.html", {"deposit": deposit})

def delete_deposit(request, pk):
    deposit = get_object_or_404(DepositScheme, id=pk)

    if request.method == "POST":
        deposit.delete()
        return redirect("deposit_list")

    return render(request, "delete_deposit.html", {"deposit": deposit})

def view_deposit(request, pk):

    deposit = get_object_or_404(DepositScheme, id=pk)

    payments = deposit.payments.all().order_by("-payment_date")

    total_paid = payments.aggregate(
        total=Sum("amount_paid")
    )["total"] or 0

    balance = (deposit.total_amount or 0) - total_paid

    context = {
        "deposit": deposit,
        "payments": payments,
        "total_paid": total_paid,
        "balance": balance,
    }

    return render(request, "view_deposit.html", context)



def reports(request):

    sales = Sale.objects.all().order_by('-date')
    payments = Payment.objects.all().order_by('-created_at')
    products = Product.objects.all()
    suppliers = Supplier.objects.all()
    customers = Customer.objects.all()

    total_sales = sales.aggregate(total=Sum('final_amount'))['total'] or 0
    total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_balance = total_sales - total_paid

    total_quantity_sold = sales.aggregate(total=Sum('quantity'))['total'] or 0
    total_transactions = sales.count()
    average_sale_value = round((total_sales / total_transactions), 2) if total_transactions else 0

    collection_rate = round((total_paid / total_sales) * 100, 2) if total_sales else 0

    total_products = products.count()
    low_stock = products.filter(stock_quantity__lt=10)
    out_of_stock = products.filter(stock_quantity=0)
    total_stock_quantity = products.aggregate(total=Sum('stock_quantity'))['total'] or 0
    stock_value = products.aggregate(total=Sum(F('unit_price') * F('stock_quantity')))['total'] or 0

    total_customers = customers.count()
    customers_with_balance = (
        sales.filter(customer_name__isnull=False, final_amount__gt=F('sub_total'))
        .values_list('customer_name_id', flat=True)
        .distinct()
        .count()
    )

    total_payments = payments.aggregate(total=Sum('amount_paid'))['total'] or 0

    recent_sales = sales[:10]
    for sale in recent_sales:
        sale.balance = (sale.final_amount or 0) - (sale.sub_total or 0)

    recent_payments = payments[:10]

    top_products = (
        sales.values('name__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    total_suppliers = suppliers.count()

    context = {
        'sales': sales,
        'recent_sales': recent_sales,
        'total_sales': total_sales,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'total_quantity_sold': total_quantity_sold,
        'total_transactions': total_transactions,
        'average_sale_value': average_sale_value,
        'collection_rate': collection_rate,
        'expected_money': total_sales,
        'products': products,
        'total_products': total_products,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total_stock_quantity': total_stock_quantity,
        'stock_value': stock_value,
        'customers': customers,
        'total_customers': total_customers,
        'customers_with_balance': customers_with_balance,
        'payments': payments,
        'recent_payments': recent_payments,
        'total_payments': total_payments,
        'top_products': top_products,
        'total_suppliers': total_suppliers,
    }

    return render(request, 'reports.html', context)