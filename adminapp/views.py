from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, date, timedelta
from decimal import Decimal
from nyondoapp.models import Sale, Payment, Customer, Product, Stock
from django.db.models import Sum, Max, F
from django.utils import timezone
from .forms import SupplierForm, SupplierPaymentForm
from .models import Supplier, DepositScheme, DepositPayment
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from nyondoapp.models import Employee
from .forms import EmployeeCreationForm
from nyondoapp.utils import role_required
from nyondoapp.utils import (admin_required,manager_required,attendant_required,)


@role_required(["attendant", "admin"])
def _deposit_summary(deposit):
    payments_total = deposit.payments.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0.00")
    saved_paid = deposit.amount_paid or Decimal("0.00")
    total_paid = max(payments_total, saved_paid)
    total_amount = deposit.total_amount or Decimal("0.00")
    balance = total_amount - total_paid

    if total_paid <= 0:
        status = "Pending"
    elif balance <= 0:
        status = "Completed"
    else:
        status = "Active"

    return {
        "total_paid": total_paid,
        "balance": balance,
        "display_balance": max(balance, Decimal("0.00")),
        "status": status,
    }

@role_required(["attendant", "admin"])
def _attach_deposit_summary(deposit):
    summary = _deposit_summary(deposit)
    deposit.total_paid = summary["total_paid"]
    deposit.remaining_balance = summary["display_balance"]
    deposit.live_status = summary["status"]
    return deposit


# Create your views here.
@role_required(["admin"])
def admin_dash(request):
    today = date.today()
    sales_today = Sale.objects.filter(date__date=today)
    sales_total = sales_today.aggregate(total=Sum('final_amount'))['total'] or 0
    total_revenue = Payment.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    customer_count = Customer.objects.count() or 0
    stock_count = Product.objects.count() or 0
    low_stock = Product.objects.filter(stock_quantity__lt=F('reorder_level'))
    low_stock_count = low_stock.count() or 0
    total_sales = Sale.objects.aggregate(total=Sum('final_amount'))['total'] or 0
    total_paid = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_credit = total_sales - total_paid
    recent_sales = sales_today.order_by('-date')[:5]
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

@role_required("admin")
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
@role_required(["admin"])
def employee_list(request):
    employees = Employee.objects.all().order_by("-id")

    return render(request, "employee_list.html", {
        "employees": employees
    })

@role_required(["admin"])
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

@role_required(["admin"])
def toggle_employee_status(request, pk):

    employee = get_object_or_404(Employee, pk=pk)

    user = employee.user

    user.is_active = not user.is_active

    user.save()

    return redirect('employee_list')

@role_required(["admin"])
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


@role_required(["manager", "admin"])
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

@role_required(["admin"])
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

@role_required(["manager", "admin"])
def view_supplier(request, pk):

    supplier = get_object_or_404(Supplier,pk=pk)

    context = {
        'supplier': supplier
    }

    return render(request,'view_supplier.html', context)

@role_required(["admin"])
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

@role_required(["attendant", "admin"])
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

@role_required(["attendant", "admin"])
def deposit_dashboard(request):

    deposits = DepositScheme.objects.select_related("customer", "product").all()

    active = 0
    completed = 0
    pending = 0

    total_expected_all = Decimal("0.00")
    total_paid_all = Decimal("0.00")
    total_balance_all = Decimal("0.00")

    for d in deposits:
        _attach_deposit_summary(d)

        if d.live_status == "Pending":
            pending += 1
        elif d.live_status == "Completed":
            completed += 1
        else:
            active += 1

        total_expected_all += d.total_amount or Decimal("0.00")
        total_paid_all += d.total_paid
        total_balance_all += d.remaining_balance

    context = {
        "deposits": deposits,
        "total_deposits": deposits.count(),

        "pending_schemes": pending,
        "active_schemes": active,
        "completed_schemes": completed,

        "total_expected": total_expected_all,
        "total_paid": total_paid_all,
        "total_balance": total_balance_all,
    }

 
    return render(request, "deposit_dashboard.html", context)

@role_required(["attendant", "admin"])
def deposit_list(request):

    deposits = DepositScheme.objects.select_related("customer", "product").all()
    deposit_rows = []

    for deposit in deposits:

        payments = deposit.payments.all()  

        last_payment = payments.aggregate(
            last=Max("payment_date")
        )["last"]

        summary = _deposit_summary(deposit)

        deposit_rows.append({
            "deposit": deposit,
            "last_payment": last_payment,
            "total_paid": summary["total_paid"],
            "balance": summary["display_balance"],
            "status": summary["status"],
        })

    return render(request, "deposit_list.html", {
        "deposit_rows": deposit_rows
    })

@role_required(["attendant", "admin"])
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
        if amount_paid_value <= 0:
            status = 'Pending'
        elif balance <= 0:
            status = 'Completed'
        else:
            status = 'Active'

        deposit = DepositScheme.objects.create(
            customer=customer,
            product=product,
            total_amount=total_amount,
            quantity_expected=quantity_value,
            amount_paid=amount_paid_value,
            balance=balance,
            status=status,
        )

        if amount_paid_value > 0:
            DepositPayment.objects.create(
                scheme=deposit,
                amount_paid=amount_paid_value,
                payment_method=request.POST.get("payment_method", "cash"),
                comment="Opening deposit payment",
                received_by=request.user if request.user.is_authenticated else None,
            )

        return redirect('deposit_dashboard')

    return render(request, "add_deposit.html", {
        "customers": customers,
        "products": products
    })

@role_required(["attendant", "admin"])
def record_deposit(request, pk):
    scheme = get_object_or_404(DepositScheme, id=pk)
    _attach_deposit_summary(scheme)

    if request.method == "POST":
        amount = request.POST.get("amount_paid")
        method = request.POST.get("payment_method")
        comment = request.POST.get("comment")

        if amount:
            amount = Decimal(amount or "0")

            DepositPayment.objects.create(
                scheme=scheme,
                amount_paid=amount,
                payment_method=method,
                comment=comment,
                received_by=request.user if request.user.is_authenticated else None
            )

            # update scheme
            scheme.amount_paid = (scheme.amount_paid or Decimal("0.00")) + amount
            scheme.balance = scheme.total_amount - scheme.amount_paid

            if scheme.amount_paid <= 0:
                scheme.status = "Pending"
            elif scheme.balance <= 0:
                scheme.status = "Completed"
            else:
                scheme.status = "Active"

            scheme.save()

        return redirect('view_deposit', pk=scheme.id)

    return render(request, "record_deposit.html", {
        "scheme": scheme
    })

@role_required(["admin"])
def edit_deposit(request, pk):
    deposit = get_object_or_404(DepositScheme, id=pk)
    _attach_deposit_summary(deposit)

    if request.method == "POST":
        quantity_expected = request.POST.get("quantity_expected")
        deposit.quantity_expected = int(quantity_expected or 0)
        deposit.save()
        summary = _deposit_summary(deposit)
        deposit.amount_paid = summary["total_paid"]
        deposit.balance = summary["balance"]
        deposit.status = summary["status"]
        deposit.save(update_fields=["amount_paid", "balance", "status"])
        return redirect("deposit_list")

    return render(request, "edit_deposit.html", {"deposit": deposit})

@role_required(["admin"])
def delete_deposit(request, pk):
    deposit = get_object_or_404(DepositScheme, id=pk)

    if request.method == "POST":
        deposit.delete()
        return redirect("deposit_list")

    return render(request, "delete_deposit.html", {"deposit": deposit})

@role_required(["attendant", "admin"])
def view_deposit(request, pk):

    deposit = get_object_or_404(DepositScheme, id=pk)

    payments = deposit.payments.all().order_by("-payment_date")

    total_paid = payments.aggregate(
        total=Sum("amount_paid")
    )["total"] or Decimal("0.00")

    summary = _deposit_summary(deposit)

    context = {
        "deposit": deposit,
        "payments": payments,
        "total_paid": summary["total_paid"],
        "balance": summary["display_balance"],
        "status": summary["status"],
    }

    return render(request, "view_deposit.html", context)


@role_required(["admin"])
def reports(request):

    period = request.GET.get('period', 'all')
    today = timezone.localdate()
    sales = Sale.objects.all().order_by('-date')
    payments = Payment.objects.all().order_by('-created_at')

    if period == 'today':
        sales = sales.filter(date__date=today)
        payments = payments.filter(created_at__date=today)
    elif period == 'week':
        week_start = today - timedelta(days=today.weekday())
        sales = sales.filter(date__date__gte=week_start)
        payments = payments.filter(created_at__date__gte=week_start)
    elif period == 'month':
        sales = sales.filter(date__year=today.year, date__month=today.month)
        payments = payments.filter(created_at__year=today.year, created_at__month=today.month)
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
    low_stock = products.filter(stock_quantity__lt=F('reorder_level'))
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
        'period': period,
    }

    return render(request, 'reports.html', context)
