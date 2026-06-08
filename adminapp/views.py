from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, date, timedelta
from decimal import Decimal
from nyondoapp.models import Sale, Payment, Customer, Product, Stock
from django.db.models import Sum, Max, F
from django.utils import timezone
from .forms import SupplierForm, SupplierPaymentForm
from .models import Supplier, DepositScheme, DepositPayment, DepositWithdrawal
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from nyondoapp.models import Employee
from .forms import EmployeeCreationForm
from nyondoapp.utils import role_required
from nyondoapp.utils import (admin_required,manager_required,attendant_required,)


# this is a helper function which calculates the deposit values, total money paid, remaining balance, deposit status and returns them in a dictionary
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

# this function takes those calculated values and attaches them to deposit object
def _attach_deposit_summary(deposit):
    summary = _deposit_summary(deposit)
    deposit.total_paid = summary["total_paid"]
    deposit.remaining_balance = summary["display_balance"]
    deposit.live_status = summary["status"]
    return deposit


# Create your views here.
@role_required(["admin"])
def admin_dash(request):
    today = timezone.localdate()
    sales_today = Sale.objects.filter(date__date=today)
    sales_total = sales_today.aggregate(total=Sum('final_amount'))['total'] or 0
    # Revenue renewals each day by filtering payments by today's date
    total_revenue = Payment.objects.filter(created_at__date=today).aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    customer_count = Customer.objects.count() or 0
    stock_count = Product.objects.count() or 0
    low_stock = Product.objects.filter(stock_quantity__lt=F('reorder_level'))
    low_stock_count = low_stock.count() or 0
    total_sales = Sale.objects.aggregate(total=Sum('final_amount'))['total'] or 0
    total_paid = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
    # Ensure outstanding credit does not show negative figures
    total_credit = max(0, total_sales - total_paid)
    recent_sales = sales_today.order_by('-date')[:5]
    recent_payments = Payment.objects.order_by('-id')[:5]
    top_products = ( Sale.objects.values('name__name')   
    .annotate(total_qty=Sum('quantity')).order_by('-total_qty')[:5]
     )

    low_stock_products = Product.objects.filter(stock_quantity__lte=F('reorder_level'))

    context = {
        "sales_total": sales_total,
        "total_revenue": total_revenue,
        "customer_count": customer_count,
        "stock_count": stock_count,
        "low_stock_count": low_stock_count,
        "low_stock_products": low_stock_products,
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
            errors = {field: form.errors[field][0] for field in form.errors}
            return render(request, "create_employee.html", {
                "form": form,
                "errors": errors,
                "post_data": request.POST
            })
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
            messages.success(request, "Supplier added successfully.")
            return redirect("supplier_dashboard")
        else:
            errors = {field: form.errors[field][0] for field in form.errors}
            return render(request, "add_supplier.html", {
                "form": form,
                "errors": errors,
                "post_data": request.POST
            })
    form = SupplierForm()
    return render(request, "add_supplier.html", {"form": form})


@role_required(["manager", "admin"])
def supplier_dashboard(request):
    suppliers = Supplier.objects.all()
    total_suppliers = suppliers.count()
    pending_credit = suppliers.filter(status='pending').count()
    # Ensure the dashboard card figure doesn't show negative totals
    credits_sum = suppliers.aggregate(total=Sum('outstanding_credit'))['total'] or 0
    total_credit = max(0, credits_sum)

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
            # Ensure outstanding credit does not show negative figures
            supplier.outstanding_credit = max(0, supplier.total_amount - supplier.amount_paid)

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
            errors = {field: form.errors[field][0] for field in form.errors}
            return render(request, 'record_payment.html', {
                'form': form,
                'supplier': supplier,
                'errors': errors,
                'post_data': request.POST
            })
    else:
        form = SupplierPaymentForm()
        return render(request, 'record_payment.html', {'form': form, 'supplier': supplier})

    return render(request, 'record_payment.html', {
        'form': form,
        'supplier': supplier
    })

@role_required(["attendant", "admin"])
def deposit_dashboard(request):
    # For the table, we need all deposits with their summaries
    all_deposits_queryset = DepositScheme.objects.select_related("customer", "product").all().order_by("-id")
    all_deposits_for_table = []
    
    total_paid_all = Decimal("0.00")
    total_balance_all = Decimal("0.00")
    pending_count = 0
    active_count = 0
    completed_count = 0

    for d in all_deposits_queryset:
        updated_d = _attach_deposit_summary(d)
        all_deposits_for_table.append(updated_d)
        
        # Accumulate totals for dashboard cards
        total_paid_all += updated_d.total_paid
        total_balance_all += updated_d.remaining_balance
        
        if updated_d.live_status == "Pending":
            pending_count += 1
        elif updated_d.live_status == "Completed":
            completed_count += 1
        else: # Active
            active_count += 1

    context = {
        "deposits": all_deposits_for_table,
        "total_deposits": all_deposits_queryset.count(),
        "pending_schemes": pending_count,
        "active_schemes": active_count,
        "completed_schemes": completed_count,
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

@role_required(["admin"])
def add_deposit(request):
    customers = Customer.objects.all()
    products = Product.objects.all()

    # 1. Handle pre-selection from the URL parameter (passed from add_customer)
    preselected_customer_id = request.GET.get('customer_id')
    
    # Initialize post_data for the first GET request to pre-fill the customer field
    initial_post_data = {'customer': preselected_customer_id} if preselected_customer_id else {}

    if request.method == "POST":
        customer_id = request.POST.get("customer") or preselected_customer_id
        product_id = request.POST.get("product")
        quantity = request.POST.get("quantity_expected")
        amount_paid = request.POST.get("amount_paid")
        payment_method = request.POST.get("payment_method")

        errors = {}
        if not customer_id:
            errors['customer'] = "Please select a customer."
        if not product_id:
            errors['product'] = "Please select a product."
        if not payment_method:
            errors['payment_method'] = "Payment method is required."
        
        # 2. Strict Numeric Validation (Django-side, No JS)
        if not quantity or quantity.strip() == "" or Decimal(quantity or 0) <= 0:
            errors['quantity_expected'] = "Quantity must be greater than zero."
        else:
            try:
                quantity_value = int(quantity)
                if quantity_value <= 0:
                    errors['quantity_expected'] = "Quantity must be greater than zero."
            except (ValueError, TypeError):
                errors['quantity_expected'] = "Enter a valid whole number for quantity."

        if not amount_paid or amount_paid.strip() == "" or Decimal(amount_paid or 0) <= 0:
            errors['amount_paid'] = "Initial deposit must be greater than zero."
        else:
            try:
                amount_paid_value = Decimal(amount_paid)
                if amount_paid_value <= 0:
                    errors['amount_paid'] = "Initial deposit must be greater than zero."
            except (ValueError, Decimal.InvalidOperation):
                errors['amount_paid'] = "Enter a valid numeric amount."

        if errors:
            return render(request, "add_deposit.html", {
                "customers": customers, "products": products,
                "payment_methods": Sale.PAYMENT_METHODS,
                "errors": errors, "post_data": request.POST,
                "preselected_customer_id": preselected_customer_id
            })
            
        # 3. Save Logic
        customer = get_object_or_404(Customer, id=customer_id)
        product = get_object_or_404(Product, id=product_id)

        total_amount = (product.unit_price * Decimal(quantity_value))
        balance = total_amount - amount_paid_value

        # 4. Status Logic: Ensures tracking on Dashboard and Lists
        if balance <= 0:
            status = 'Completed'
        elif amount_paid_value > 0:
            status = 'Active'
        else:
            status = 'Pending'

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
                payment_method=payment_method,
                comment="Opening deposit payment",
                received_by=request.user if request.user.is_authenticated else None,
            )

        messages.success(request, f"Scheme for {customer.name} started. First payment of {amount_paid_value} recorded.")
        return redirect('deposit_list')  # 4. Success Redirect to List

    return render(request, "add_deposit.html", {
        "customers": customers,
        "products": products,
        "payment_methods": Sale.PAYMENT_METHODS,
        "post_data": initial_post_data,
    })

@role_required(["attendant", "admin"])
def record_deposit(request, pk):
    scheme = get_object_or_404(DepositScheme, id=pk)
    _attach_deposit_summary(scheme)

    if request.method == "POST":
        amount = request.POST.get("amount_paid")
        method = request.POST.get("payment_method")
        comment = request.POST.get("comment")

        errors = {}
        if not amount:
            errors['amount_paid'] = "Amount paid is required."
        else:
            try:
                if Decimal(amount) <= 0: errors['amount_paid'] = "Amount must be positive."
            except: errors['amount_paid'] = "Invalid amount."
            
        if not method: errors['payment_method'] = "Payment method is required."

        if errors:
            return render(request, "record_deposit.html", {
                "scheme": scheme, "errors": errors, "post_data": request.POST
            })
            
        amount = Decimal(amount)
        payment = DepositPayment.objects.create(
            scheme=scheme,
            amount_paid=amount,
            payment_method=method,
            comment=comment,
            received_by=request.user if request.user.is_authenticated else None
        )

        scheme.amount_paid = (scheme.amount_paid or Decimal("0.00")) + amount
        scheme.balance = scheme.total_amount - scheme.amount_paid

        if scheme.amount_paid <= 0:
            scheme.status = "Pending"
        elif scheme.balance <= 0:
            scheme.status = "Completed"
        else:
            scheme.status = "Active"

        scheme.save()
        messages.success(request, f"Payment of UGX {amount} recorded successfully.")
        return redirect('deposit_receipt', pk=payment.id)

    return render(request, "record_deposit.html", {
        "scheme": scheme
    })

@role_required(["admin"])
def edit_deposit(request, pk):
    deposit = get_object_or_404(DepositScheme, id=pk)
    _attach_deposit_summary(deposit)

    if request.method == "POST":
        quantity_expected = request.POST.get("quantity_expected")

        errors = {}
        if not quantity_expected:
            errors['quantity_expected'] = "Quantity is required."
        else:
            try:
                if int(quantity_expected) <= 0: errors['quantity_expected'] = "Quantity must be positive."
            except: errors['quantity_expected'] = "Invalid quantity."

        if errors:
            return render(request, "edit_deposit.html", {
                "deposit": deposit, "errors": errors, "post_data": request.POST
            })
            
        deposit.quantity_expected = int(quantity_expected or 0)
        deposit.save()
        summary = _deposit_summary(deposit)
        deposit.amount_paid = summary["total_paid"]
        deposit.balance = summary["balance"]
        deposit.status = summary["status"]
        deposit.save(update_fields=["amount_paid", "balance", "status"])
        messages.success(request, "Deposit scheme updated successfully.")
        return redirect("deposit_list")

    return render(request, "edit_deposit.html", {"deposit": deposit})

@role_required(["admin"])
def delete_deposit(request, pk):
    deposit = get_object_or_404(DepositScheme, id=pk)

    if request.method == "POST":
        deposit.delete()
        messages.success(request, "Deposit scheme deleted successfully.")
        return redirect("deposit_list")

    return render(request, "delete_deposit.html", {"deposit": deposit})

@role_required(["attendant", "admin"])
def view_deposit(request, pk):

    deposit = get_object_or_404(DepositScheme, id=pk)

    _attach_deposit_summary(deposit)
    payments = deposit.payments.all().order_by("-payment_date")

    total_paid = payments.aggregate(
        total=Sum("amount_paid")
    )["total"] or Decimal("0.00")

    summary = _deposit_summary(deposit)

    context = {
        "deposit": deposit,
        "payments": payments,
        "total_paid": summary["total_paid"],
        "withdrawals": deposit.withdrawals.all().order_by("-withdrawal_date"),
        "balance": summary["display_balance"],
        "status": summary["status"],
    }

    return render(request, "view_deposit.html", context)

@role_required(["attendant", "admin"])
def withdraw_deposit(request, pk):

    deposit = get_object_or_404(DepositScheme, id=pk)
    _attach_deposit_summary(deposit)

    if request.method == "POST":

        quantity = request.POST.get("quantity")
        comment = request.POST.get("comment")

        errors = {}
        if not quantity:
            errors['quantity'] = "Quantity is required."
        else:
            try:
                if int(quantity) <= 0: errors['quantity'] = "Quantity must be positive."
            except: errors['quantity'] = "Invalid quantity."

        if errors:
            return render(request, "withdraw_deposit.html", {
                "deposit": deposit, "errors": errors, "post_data": request.POST
            })
            
        withdrawal = DepositWithdrawal.objects.create(
            scheme=deposit,
            quantity_withdrawn=int(quantity),
            comment=comment,
            received_by=request.user if request.user.is_authenticated else None,
        )

        # Force status to Withdrawn and bypass model's auto-status logic
        DepositScheme.objects.filter(pk=deposit.pk).update(status="Withdrawn")

        messages.success(request, "Withdrawal recorded successfully.")
        return redirect("withdraw_receipt", pk=withdrawal.id)

    return render(request, "withdraw_deposit.html", {
        "deposit": deposit
    })

@role_required(["attendant", "admin"])
def deposit_receipt(request, pk):
    payment = get_object_or_404(DepositPayment, id=pk)
    summary = _deposit_summary(payment.scheme)

    context = {
        "payment": payment,
        "deposit": payment.scheme,
        "summary": summary,
    }

    return render(request, "deposit_receipt.html", context)

@role_required(["attendant", "admin"])
def withdraw_receipt(request, pk):

    withdrawal = get_object_or_404(DepositWithdrawal, id=pk)

    context = {
        "withdrawal": withdrawal
    }

    return render(request, "withdraw_receipt.html", context)

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
    # Ensure figures don't show as negative
    total_balance = max(0, total_sales - total_paid)
    
    # Determine date range for the period
    start_date_for_period = None
    end_date_for_period = today

    if period == 'today':
        start_date_for_period = today
    elif period == 'week':
        start_date_for_period = today - timedelta(days=today.weekday())
    elif period == 'month':
        start_date_for_period = today.replace(day=1)
    elif period == 'all':
        earliest_sale = Sale.objects.order_by('date').first()
        earliest_payment = Payment.objects.order_by('created_at').first()
        if earliest_sale and earliest_payment:
            start_date_for_period = min(earliest_sale.date.date(), earliest_payment.created_at.date())
        elif earliest_sale:
            start_date_for_period = earliest_sale.date.date()
        elif earliest_payment:
            start_date_for_period = earliest_payment.created_at.date()
        else:
            start_date_for_period = today # Default if no data

    # Calculate total reporting days
    total_reporting_days = (end_date_for_period - start_date_for_period).days + 1 if start_date_for_period else 0


    total_quantity_sold = sales.aggregate(total=Sum('quantity'))['total'] or 0
    total_transactions = sales.count()
    average_sale_value = round((total_sales / total_transactions), 2) if total_transactions else 0

    collection_rate = round((total_paid / total_sales) * 100, 2) if total_sales else 0

    # Financial Performance Metrics
    cogs = Decimal('0.00')
    for sale in sales:
        if sale.name and sale.name.cost_price:
            cogs += sale.quantity * sale.name.cost_price
    gross_profit = total_sales - cogs
    net_profit = gross_profit # Assuming no other operational expenses are tracked in this system

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

    total_payments_count = payments.count() # Renamed to avoid conflict with total_paid amount

    recent_sales = sales[:10]
    for sale in recent_sales:
        sale.balance = (sale.final_amount or Decimal('0.00')) - (sale.payment.amount_paid if sale.payment else Decimal('0.00')) # Assuming payment is linked
        sale.balance = max(Decimal('0.00'), sale.balance) # Ensure balance is not negative

    recent_payments = payments[:10]


    top_products = (
        sales.values('name__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    total_suppliers = suppliers.count()

    # New Business Activity Summary metrics
    new_products_added = Product.objects.filter(date_added__date__range=(start_date_for_period, end_date_for_period)).count() if start_date_for_period else 0
    new_customers_registered = Customer.objects.filter(date_joined__date__range=(start_date_for_period, end_date_for_period)).count() if start_date_for_period else 0

    # Outstanding Balances Report
    outstanding_customers_data = []
    for customer in Customer.objects.all():
        customer_sales_total = Sale.objects.filter(customer_name=customer, date__date__range=(start_date_for_period, end_date_for_period)).aggregate(total=Sum('final_amount'))['total'] or Decimal('0.00')
        customer_payments_total = Payment.objects.filter(customer=customer, created_at__date__range=(start_date_for_period, end_date_for_period)).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        customer_balance = customer_sales_total - customer_payments_total

        if customer_balance > 0:
            last_sale_date = Sale.objects.filter(customer_name=customer).aggregate(latest_date=Max('date'))['latest_date']
            last_payment_date = Payment.objects.filter(customer=customer).aggregate(latest_date=Max('created_at'))['latest_date']
            last_transaction_date = None
            if last_sale_date and last_payment_date:
                last_transaction_date = max(last_sale_date, last_payment_date)
            elif last_sale_date:
                last_transaction_date = last_sale_date
            elif last_payment_date:
                last_transaction_date = last_payment_date

            outstanding_customers_data.append({
                'customer_name': customer.name,
                'outstanding_balance': customer_balance,
                'last_transaction_date': last_transaction_date,
            })

    # Inventory Status Report
    inventory_status_data = []
    for product in Product.objects.all():
        status = "In Stock"
        if product.stock_quantity == 0:
            status = "Out of Stock"
        elif product.stock_quantity <= product.reorder_level:
            status = "Low Stock"
        inventory_status_data.append({
            'product_name': product.name,
            'current_quantity': product.stock_quantity,
            'status': status,
        })

    # Management Recommendations
    recommendations = []
    if low_stock.exists():
        recommendations.append("Products that require restocking: " + ", ".join([p.name for p in low_stock[:3]]) + ("..." if low_stock.count() > 3 else ""))
    if outstanding_customers_data:
        recommendations.append("Customers with outstanding balances need follow-up.")
    if gross_profit < 0: # Simple threshold for monitoring expenses
        recommendations.append("Gross profit is negative. Review pricing and costs.")
    if top_products:
        recommendations.append("Prioritize high-performing products: " + ", ".join([p['name__name'] for p in top_products[:3]]) + ("..." if top_products.count() > 3 else ""))

    context = {
        'sales': sales,
        'recent_sales': recent_sales,
        'total_sales': total_sales,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'total_quantity_sold': total_quantity_sold,
        'total_transactions': total_transactions,
        'average_sale_value': average_sale_value,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        'collection_rate': collection_rate,
        'expected_money': total_sales,
        'products': products,
        'total_products': total_products,
        "date_generated": timezone.now(),
        "generated_by": request.user.username,
        "total_reporting_days": total_reporting_days,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total_stock_quantity': total_stock_quantity,
        'stock_value': stock_value,
        'customers': customers,
        'total_customers': total_customers,
        'customers_with_balance': customers_with_balance,
        'payments': payments, # This is the queryset for the period
        'recent_payments': recent_payments,
        'total_payments': total_payments_count, # This is the count of payments
        'top_products': top_products,
        'total_suppliers': total_suppliers,
        'period': period,
        "new_products_added": new_products_added,
        "new_customers_registered": new_customers_registered,
        "outstanding_customers_data": outstanding_customers_data,
        "inventory_status_data": inventory_status_data,
        "recommendations": recommendations,
    }

    return render(request, 'reports.html', context)
