from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, date
from nyondoapp.models import Sale, Payment, Customer, Product
from django.db.models import Sum
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
    active_deposits = deposits.filter(is_completed=False)
    completed_deposits = deposits.filter(is_completed=True)

    context = {
        "total_deposits": deposits.count(),
        "active_deposits": active_deposits,
        "completed_deposits": completed_deposits,
    }
    return render(request, "deposit_dashboard.html", context)

def record_deposit(request, scheme_id):
    scheme = get_object_or_404(DepositScheme, id=scheme_id)

    if request.method == "POST":
        amount = request.POST.get("amount_paid")
        method = request.POST.get("payment_method")
        comment = request.POST.get("comment")

        if amount:
            amount = float(amount)

            # create payment
            DepositPayment.objects.create(
                scheme=scheme,
                amount_paid=amount,
                payment_method=method,
                comment=comment,
                received_by=request.user
            )

            # update scheme
            scheme.amount_paid += amount
            scheme.balance = scheme.total_amount - scheme.amount_paid

            if scheme.balance <= 0:
                scheme.status = "Completed"

            scheme.save()

        return redirect('deposit_dashboard')

    return render(request, 'record_deposit.html', {
        'scheme': scheme
    })

from django.shortcuts import render
from .models import DepositScheme, DepositPayment
from django.db.models import Sum

def deposit_dashboard(request):

    active_schemes = DepositScheme.objects.filter(status="Active").count()
    completed_schemes = DepositScheme.objects.filter(status="Completed").count()

    total_paid = DepositPayment.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0

    total_balance = DepositScheme.objects.aggregate(
        total=Sum('balance')
    )['total'] or 0

    recent_payments = DepositPayment.objects.select_related('scheme').order_by('-payment_date')[:5]

    context = {
        'active_schemes': active_schemes,
        'completed_schemes': completed_schemes,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'recent_payments': recent_payments,
    }

    return render(request, 'deposit_dashboard.html', context)



def deposit_list(request):
    payments = DepositPayment.objects.select_related('scheme').order_by('-payment_date')

    return render(request, 'deposit_list.html', {'payments': payments})