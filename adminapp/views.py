from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, date
from nyondoapp.models import Sale, Payment, Customer, Product
from django.db.models import Sum, Max
from .forms import SupplierForm, SupplierPaymentForm
from .models import Supplier, DepositScheme, DepositPayment

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

        deposit = DepositScheme.objects.create(
            customer=customer,
            product=product,
            quantity_expected=quantity,
            amount_paid=amount_paid,
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