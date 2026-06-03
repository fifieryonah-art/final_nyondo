import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import F
from django.utils import timezone
from .models import Stock, Product, Sale, Payment, Customer, Employee, Expense
from decimal import Decimal
from .forms import CustomerForm, ExpenseForm
from adminapp.models import Supplier, DepositScheme, DepositPayment, SupplierPayment
from django.db import transaction
from django.db.models import F, DecimalField, ExpressionWrapper
from django.db.models import Sum
from .stock_services import update_stock
from .utils import role_required
#from django.contrib.auth.decorators import login_required

# Create your views here.
#Authentication pages
# LOGIN PAGE
def indexPage(request):
    return render(request, 'index.html')
def loginPage(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        errors = {}

        if not username:
            errors['username'] = "Username is required."
        if not password:
            errors['password'] = "Password is required."

        if errors:
            return render(request, "login.html", {'errors': errors, 'post_data': request.POST})

        # authenticate user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # login user
            login(request, user)

            # SUPERUSER AUTHORIZATION
            if user.is_superuser:
                return redirect("admin_dash")

            # EMPLOYEE AUTHORIZATION
            try:
                employee = Employee.objects.get(user=user)
                # ADMIN
                if employee.role == "admin":
                    return redirect("admin_dash")
                # MANAGER
                elif employee.role == "manager":
                    return redirect("stock")
                # SALES ATTENDANT
                elif employee.role == "attendant":
                    return redirect("sales_dash")

                else:
                    messages.error(request, "Unauthorized role")
                    return redirect("login")

            except Employee.DoesNotExist:
                messages.error(request, "Employee profile not found")
                return redirect("login")

        else:
            messages.error(request, "Invalid username or password")
            return render(request, "login.html", {'post_data': request.POST})
            
    return render(request, "login.html")


# LOGOUT
def logout_user(request):
    logout(request)
    return redirect("login")

#stock views
@role_required(["manager", "admin"])
def stockPage(request):
    products = Product.objects.all()
    recent_stock = Stock.objects.select_related("product", "supplier", "entered_by").order_by("-date_arrival", "-time_arrival")[:10]
    total_products = products.count()
    low_stock_items = products.filter(stock_quantity__lte=F('reorder_level'))
    # Calculate stock value for all products and ensure low_stock_items have it
    for product in products:
        product.stock_value = product.stock_quantity * product.cost_price
    low_stock_count = low_stock_items.count()
    out_of_stock_count = products.filter(stock_quantity=0).count()

    # Optimized total value calculation using aggregation
    total_value = products.aggregate(
        total=Sum(F('stock_quantity') * F('cost_price'), output_field=DecimalField())
    )['total'] or 0

    context = {
        "total_products": total_products,
        "low_stock": low_stock_count,
        "out_of_stock": out_of_stock_count,
        "total_value": total_value,
        "low_stock_items": low_stock_items,
        "recent_stock": recent_stock,
        "products": products,
    }
    return render(request, 'stock.html', context)

@role_required(["manager", "admin"])
def stock_list(request):
    products = Product.objects.all().order_by("name")
    for product in products:
        product.stock_value = product.stock_quantity * product.cost_price
    low_stock_items = products.filter(stock_quantity__lt=F("reorder_level"))
    stock_value = sum(product.stock_value for product in products)
    return render(request, "stock_list.html", {
        "products": products,
        "low_stock_items": low_stock_items,
        "stock_value": stock_value,
    })

@role_required(["manager", "admin"])
def stock_records(request):
    stocks = Stock.objects.select_related("product", "supplier", "entered_by").order_by("-date_arrival", "-time_arrival")
    return render(request, "stock_records.html", {"stocks": stocks})

@role_required(["manager", "admin"])
@transaction.atomic
def add_stock(request):
    products = Product.objects.all()
    suppliers = Supplier.objects.all()

    if request.method == "POST":
        supplier_id = request.POST.get("supplier")
        comments = request.POST.get("comments")
        is_paid = "is_paid" in request.POST
        
        # Since template only has is_paid, if it's not paid, it's on credit
        is_on_credit = not is_paid

        p_id = request.POST.get("product")
        qty_str = request.POST.get("quantity")
        cp_str = request.POST.get("cost_price")
        up_str = request.POST.get("unit_price")

        errors = {}
        if not supplier_id:
            errors['supplier'] = "Please select a supplier."
        if not p_id:
            errors['product'] = "Please select a product."
        
        try:
            qty = int(qty_str or 0)
            if qty <= 0:
                errors['quantity'] = "Quantity must be greater than zero."
        except ValueError:
            errors['quantity'] = "Enter a valid quantity."

        try:
            cp = Decimal(cp_str or 0)
            if cp <= 0:
                errors['cost_price'] = "Cost price must be greater than zero."
        except (ValueError, Decimal.InvalidOperation):
            errors['cost_price'] = "Enter a valid cost price."

        try:
            up = Decimal(up_str or 0)
            if up <= 0:
                errors['unit_price'] = "Selling price must be greater than zero."
            elif cp > 0 and up < cp:
                errors['unit_price'] = "Selling price cannot be lower than cost price."
        except (ValueError, Decimal.InvalidOperation):
            errors['unit_price'] = "Enter a valid selling price."

        if errors:
            return render(request, "add_stock.html", {
                "products": products,
                "suppliers": suppliers,
                "errors": errors,
                "post_data": request.POST
            })

        supplier = get_object_or_404(Supplier, id=supplier_id)
        batch_total_cost = Decimal("0.00")

        product = get_object_or_404(Product, id=p_id)
        item_total = cp * qty
        batch_total_cost += item_total

        # Update product prices and inventory
        product.cost_price = cp
        product.unit_price = up
        product.save(update_fields=["cost_price", "unit_price"])

        try:
            update_stock(product, qty, user=request.user, reason="stock_purchase")
        except ValueError as e:
            messages.error(request, f"Stock update failed: {e}")
            return render(request, "add_stock.html", {"products": products, "suppliers": suppliers, "post_data": request.POST})

        Stock.objects.create(
            product=product,
            supplier=supplier,
            quantity=qty,
            comments=comments,
            total_cost=item_total,
            is_on_credit=is_on_credit,
            is_paid=is_paid,
            entered_by=request.user,
        )

        # Update supplier's master financials
        supplier.total_amount += batch_total_cost
        if is_paid:
            supplier.amount_paid += batch_total_cost
            # Create a payment record for tracking history
            SupplierPayment.objects.create(
                supplier=supplier,
                amount_paid=batch_total_cost,
                comment=f"Direct payment for stock supply batch. {comments or ''}"
            )
        
        supplier.outstanding_credit = max(0, supplier.total_amount - supplier.amount_paid)
        
        if supplier.outstanding_credit <= 0:
            supplier.status = "Paid"
        elif supplier.amount_paid > 0:
            supplier.status = "Partial"
        else:
            supplier.status = "Pending"
        
        supplier.save()

        messages.success(request, "Stock records added successfully!")
        return redirect("stock")

    context = {
        "products": products,
        "suppliers": suppliers,

    }

    return render(request, "add_stock.html",context)

@role_required(["admin"])
@transaction.atomic
def stock_delete(request, pk):
    stock = get_object_or_404(Stock, pk=pk)

    if request.method == "POST":
        product = stock.product
        supplier = stock.supplier
        
        # Reverse stock movement
        if product:
            update_stock(product, -stock.quantity)

        # Sync Supplier Financials
        if supplier:
            supplier.total_amount -= stock.total_cost
            if stock.is_paid:
                supplier.amount_paid -= stock.total_cost

            supplier.outstanding_credit = max(0, supplier.total_amount - supplier.amount_paid)
            supplier.status = "Paid" if supplier.outstanding_credit <= 0 else ("Partial" if supplier.amount_paid > 0 else "Pending")
            supplier.save()

        stock.delete()

        messages.success(request, "Stock deleted successfully")
        return redirect('stock_list')

    return render(request, 'stock_delete.html', {'stock': stock})

@role_required(["manager", "admin"])
@transaction.atomic
def stock_update(request, pk):
    stock = get_object_or_404(Stock, pk=pk)

    products = Product.objects.all()
    suppliers = Supplier.objects.all()

    old_quantity = stock.quantity
    old_cost = stock.total_cost

    if request.method == "POST":
        new_product = get_object_or_404(Product, id=request.POST.get('product'))
        new_supplier = get_object_or_404(Supplier, id=request.POST.get('supplier'))

        new_quantity = int(request.POST.get('quantity') or 0)
        comments = request.POST.get('comments')
        total_cost = Decimal(request.POST.get('total_cost') or 0)

        # Handle potential change in product or supplier
        if stock.product_id != new_product.id:
            if stock.product:
                update_stock(stock.product, -old_quantity)
            update_stock(new_product, new_quantity)
        else:
            update_stock(new_product, (new_quantity - old_quantity))
            

        # Sync Financials - Fixed logic to handle same or different suppliers correctly
        if stock.supplier_id == new_supplier.id:
            # Updating the same supplier: calculate net change on one instance to prevent overwrites
            supplier = stock.supplier
            if supplier:
                supplier.total_amount = supplier.total_amount - old_cost + total_cost
                if stock.is_paid:

                    supplier.outstanding_credit = max(0, supplier.total_amount - supplier.amount_paid)
                    supplier.status = "Paid" if supplier.outstanding_credit <= 0 else ("Partial" if supplier.amount_paid > 0 else "Pending")
                    supplier.save()
        else:
            # Supplier changed: subtract from old supplier
            if stock.supplier:
                old_supplier = stock.supplier
                old_supplier.total_amount -= old_cost
                if stock.is_paid:
                    old_supplier.amount_paid -= old_cost
                old_supplier.outstanding_credit = max(0, old_supplier.total_amount - old_supplier.amount_paid)
                old_supplier.status = "Paid" if old_supplier.outstanding_credit <= 0 else ("Partial" if old_supplier.amount_paid > 0 else "Pending")
                old_supplier.save()

            # Add to new supplier
            new_supplier.total_amount += total_cost
            if stock.is_paid:
                new_supplier.amount_paid += total_cost
            new_supplier.outstanding_credit = max(0, new_supplier.total_amount - new_supplier.amount_paid)
            new_supplier.status = "Paid" if new_supplier.outstanding_credit <= 0 else ("Partial" if new_supplier.amount_paid > 0 else "Pending")
            new_supplier.save()

        stock.comments = comments
        stock.total_cost = total_cost
        stock.product = new_product
        stock.supplier = new_supplier
        stock.save()

        messages.success(request, "Stock updated successfully")
        return redirect('stock_list')

    return render(request, 'stock_update.html', {
        'stock': stock,
        'products': products,
        'suppliers': suppliers
    })

@role_required(["manager", "admin"])
def low_stock_items(request):

    # GET LOW STOCK PRODUCTS
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=F('reorder_level')
    ).annotate(

        # CALCULATE STOCK VALUE
        stock_value=ExpressionWrapper(
            F('stock_quantity') * F('cost_price'),
            output_field=DecimalField()
        )

    )

    context = {

        'low_stock_items': low_stock_products

    }

    return render(
        request,
        'low_stock_items.html',
        context
    )

@role_required(["manager", "admin"])
def stock_report(request):

    stocks = Stock.objects.all()
    total_stock = stocks.count()
    total_value = stocks.aggregate(total=Sum('total_cost'))['total'] or 0
    paid_stock = stocks.filter(is_paid=True).count()
    credit_stock = stocks.filter(is_paid=False).count()

    context = {
        "stocks": stocks,
        "total_stock": total_stock,
        "total_value": total_value,
        "paid_stock": paid_stock,
        "credit_stock": credit_stock,
    }

    return render(request, "stock_report.html", context)

@role_required(["manager", "admin"])
def stock_supplier_dashboard(request):
    suppliers = Supplier.objects.all().order_by('id')
    total_suppliers = suppliers.count()
    pending_credit = suppliers.filter(status__iexact='pending').count()
    credits_sum = suppliers.aggregate(total=Sum('outstanding_credit'))['total'] or 0
    total_credit = max(0, credits_sum)

    context = {
        'suppliers': suppliers,
        'total_suppliers': total_suppliers,
        'pending_credit': pending_credit,
        'total_credit': total_credit,
    }

    return render(request, 'stock_supplier_dashboard.html', context)


#product page
@role_required(["admin"])
def add_product(request):
    from .forms import ProductForm
    form = ProductForm()
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.entered_by = request.user
            product.save()
            messages.success(request, 'Product added successfully.')
            return redirect('product_list')
        else:
            # Extract errors from the form and pass them to the template
            errors = {field: form.errors[field][0] for field in form.errors}
            return render(request, 'add_product.html', {
                'form': form,
                'errors': errors,
                'post_data': request.POST
            })
    form = ProductForm() # For GET request
    return render(request, 'add_product.html', {'form': form, 'post_data': request.POST})

@role_required(["attendant", "admin"])
def product_list(request):
    products = Product.objects.all()

    context = {
        'products': products
    }

    return render(request, 'product_list.html', context)

@role_required(["admin"])
def update_product(request, pk):
    product = get_object_or_404( Product, pk=pk)

    if request.method == "POST":
        errors = {}
        name = request.POST.get("name")
        description = request.POST.get("description")
        specification = request.POST.get("specification")
        product_type = request.POST.get("type")
        reorder_level_str = request.POST.get("reorder_level")

        if not name:
            errors['name'] = "Product name is required."

        try:
            cost_price = Decimal(request.POST.get("cost_price") or 0)
            if cost_price <= 0:
                errors['cost_price'] = "Cost price must be greater than zero."
        except (ValueError, Decimal.InvalidOperation):
            errors['cost_price'] = "Enter a valid cost price."

        try:
            unit_price = Decimal(request.POST.get("unit_price") or 0)
            if unit_price <= 0:
                errors['unit_price'] = "Selling price must be greater than zero."
            elif cost_price > 0 and unit_price < cost_price:
                errors['unit_price'] = "Selling price cannot be lower than cost price."
        except (ValueError, Decimal.InvalidOperation):
            errors['unit_price'] = "Enter a valid selling price."

        try:
            new_qty = int(request.POST.get("stock_quantity") or 0)
            if new_qty < 0:
                errors['stock_quantity'] = "Quantity cannot be negative."
        except ValueError:
            errors['stock_quantity'] = "Quantity must be an integer."

        try:
            reorder_level = int(reorder_level_str or 0)
            if reorder_level < 0:
                errors['reorder_level'] = "Reorder level cannot be negative."
        except ValueError:
            errors['reorder_level'] = "Reorder level must be an integer."

        if errors:
            return render(request, 'update_product.html', {'product': product, 'errors': errors, 'post_data': request.POST})

        # Update stock via centralized service to keep audit/validation consistent
        delta = new_qty - product.stock_quantity
        if delta != 0:
            try:
                update_stock(product, delta, user=request.user, reason=f"product_update:{product.id}")
            except ValueError as e:
                messages.error(request, f"Unable to update stock: {e}")
                return render(request, 'update_product.html', {'product': product})

        product.name = name
        product.description = description
        product.specification = specification
        product.type = product_type
        product.cost_price = cost_price
        product.unit_price = unit_price
        product.reorder_level = reorder_level
        product.entered_by = request.user 
        product.save()

        messages.success(request,"Product updated successfully")
        return redirect("product_list")

    context ={
        'product': product
    }
    # Initial load, populate post_data with current product values
    context['post_data'] = product.__dict__

    return render(request, 'update_product.html', context)

@role_required(["admin"])
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted successfully")
        return redirect('product_list')

    return render(request, 'delete_product.html', {
        'product': product
    })

# payment views
@role_required(["attendant", "admin"])
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

# SALES VIEWS
@role_required(["attendant", "admin"])
def employee_dash(request):

    today = timezone.localdate()

    # today's sales only
    today_sales = Sale.objects.filter(date__date=today)

    # today's revenue (NOT all-time)
    today_revenue = today_sales.aggregate(
        total=Sum('final_amount')
    )['total'] or 0

    total_sales = today_sales.count()

    # today's payments 
    today_payments = Payment.objects.filter(created_at__date=today)

    total_paid = today_payments.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0

    products = Product.objects.all()

    low_stock_items = products.filter(stock_quantity__lt=F('reorder_level'))

    for item in low_stock_items:
        item.stock_value = item.stock_quantity * item.unit_price

    recent_sales = today_sales.order_by('-date')[:10]

    context = {
        "total_sales": total_sales,
        "total_revenue": today_revenue,
        "total_paid": total_paid,
        "recent_sales": recent_sales,
        "products": products,
        "low_stock_items": low_stock_items,
        "low_stock_count": low_stock_items.count(),
    }

    return render(request, 'employee_dash.html', context)

@role_required(["attendant", "admin"])
def sales_dash(request):
    today = timezone.localdate()
    products = Product.objects.all()
    sales = Sale.objects.filter(date__date=today).order_by('-date')

    total_products = products.count()
    total_sales = sales.count()

    # Calculate total revenue for the current day only
    total_revenue = sales.aggregate(Sum('final_amount'))['final_amount__sum'] or 0
    total_items_sold = sales.aggregate(Sum('quantity'))['quantity__sum'] or 0

    transport_total = sales.aggregate(
        Sum('transport')
    )['transport__sum'] or 0

    low_stock = Product.objects.filter(stock_quantity__lt=F('reorder_level'))
    for product in low_stock:
        product.stock_value = product.stock_quantity * product.unit_price

    low_stock_count = low_stock.count()

    # Aggregate sales by product name and sum the quantities
    top_selling_items = (
        Sale.objects.filter(name__isnull=False)
        .values('name__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    supplier_credit = Supplier.objects.aggregate(total=Sum('outstanding_credit'))['total'] or 0
    # Update Sales Dashboard card to show only new deposits for today
    deposits = DepositScheme.objects.filter(payment_date__date=today).count()

    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_items_sold': total_items_sold,
        'total_revenue': total_revenue,
        'transport_total': transport_total,
        'supplier_credit': supplier_credit,
        'deposits': deposits,
        'low_stock': low_stock,
        'low_stock_count': low_stock_count,
        'top_selling_items': top_selling_items,
            }
    return render(request, "sales_dash.html", context)

@role_required(["attendant", "admin"])
def detailed_sales_report(request):
    """Comprehensive sales report showing payment details and re-print options."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    sales = Sale.objects.select_related('name', 'customer_name', 'payment').all().order_by('-date')
    
    if start_date:
        sales = sales.filter(date__date__gte=start_date)
    if end_date:
        sales = sales.filter(date__date__lte=end_date)
        
    return render(request, 'detailed_sales_report.html', {
        'sales': sales,
        'start_date': start_date,
        'end_date': end_date,
    })

@role_required(["attendant", "admin"])
def sales_list(request):

    today = timezone.localdate()
    sales = Sale.objects.filter(date__date=today).order_by('-date')
    context = {
        'sales': sales,
        'list_date': today,
    }
    return render(request, 'sales_list.html', context)

@role_required(["attendant", "admin"])
def top_selling_report(request):
    """View to see all top selling items from best to least sold."""
    top_selling = (
        Sale.objects.values('name__name', 'name__type', 'unit_price')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum('sub_total')
        )
        .order_by('-total_qty')
    )
    
    return render(request, 'top_selling_report.html', {'top_selling': top_selling})

@role_required(["attendant", "admin"])
@transaction.atomic
def add_sales(request):
    products = Product.objects.all()
    customers = Customer.objects.all()

    if request.method == 'POST':

        
        # CUSTOMER (TYPE OR SELECT)
        
        customer_input = request.POST.get('customer_name')

        if not customer_input:
            messages.error(request, 'Customer name is required.')
            return render(request, 'add_sales.html', {
                'products': products, 'customers': customers,
                'payment_methods': Sale.PAYMENT_METHODS,
            })

        # Handle both ID selection (numeric) and new name input (string)
        if customer_input.isdigit():
            customer = get_object_or_404(Customer, id=customer_input)
        else:
            # Create or get customer by name. Defaults ensure mandatory fields are filled.
            customer, created = Customer.objects.get_or_create(
                name=customer_input,
                defaults={
                    'phone': '0000000000',
                    'nin': f'TEMP-{uuid.uuid4().hex[:8].upper()}'
                }
            )

        
        # OTHER FIELDS
        
        distance = Decimal(request.POST.get('distance') or 0)
        payment_method = request.POST.get('payment_method')
        comments = request.POST.get('comments', '')

        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')

        use_transport = request.POST.get('use_transport')  # optional checkbox

        
        # VALIDATION
        
        if not product_ids or len(product_ids) != len(quantities):
            messages.error(request, 'Please add at least one product to the sale.')
            return render(request, 'add_sales.html', {
                'products': products, 'customers': customers,
                'payment_methods': Sale.PAYMENT_METHODS,
            })

        consolidated_cart = {}
        for p_id, q_raw in zip(product_ids, quantities):
            qty = int(q_raw or 0)
            if qty <= 0:
                messages.error(request, 'Quantity must be greater than zero.')
                return render(request, 'add_sales.html', {
                    'products': products, 'customers': customers,
                    'payment_methods': Sale.PAYMENT_METHODS,
                })
            consolidated_cart[p_id] = consolidated_cart.get(p_id, 0) + qty

        sales_data = []
        for product_id, total_qty in consolidated_cart.items():
            product = get_object_or_404(Product, id=product_id)
            if product.stock_quantity < total_qty:
                messages.error(request, f"Sale Failed: {product.name} is insufficient. Available: {product.stock_quantity}.")
                return render(request, 'add_sales.html', {
                    'products': products, 'customers': customers,
                    'payment_methods': Sale.PAYMENT_METHODS,
                })
            sales_data.append({
                'product': product,
                'quantity': total_qty
            })

        
        # CREATE SALES RECORDS
        
        created_sale_ids = []

        for item in sales_data:
            product = item['product']
            quantity = item['quantity']

            sub_total = Decimal(quantity) * product.unit_price

            
            # TRANSPORT LOGIC (OPTIONAL)
            
            transport_fee = Decimal('0.00')

            if use_transport:
                if not (distance <= Decimal('10') and sub_total >= Decimal('500000')):
                    transport_fee = Decimal('30000.00')

            final_amount = sub_total + transport_fee

            
            # CREATE SALE
            
            sale = Sale.objects.create(
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
                recorded_by=request.user if request.user.is_authenticated else None,
                receipt_number=f"SALE-{uuid.uuid4().hex[:8].upper()}",
            )
            # Reduce stock via centralized service
            try:
                update_stock(product, -quantity, user=request.user, reason=f"sale:{sale.id}")
            except ValueError as e:
                messages.error(request, f"Sale Failed: {product.name} - {e}")
                return redirect('add_sales')

            created_sale_ids.append(str(sale.id))
            
        # Save sales IDs to session and redirect immediately to Payment
        request.session['pending_sale_ids'] = created_sale_ids
        request.session.modified = True
        return redirect('add_payment')
        
    return render(request, 'add_sales.html', {
        'products': products,
        'customers': customers,
        'payment_methods': Sale.PAYMENT_METHODS,
    })

@role_required(["admin"])
def add_customer(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, "Customer added successfully.")
            if customer.on_scheme:
                return redirect(f"{reverse('add_deposit')}?customer_id={customer.id}")
            return redirect("customer_list")
        else:
            errors = {field: form.errors[field][0] for field in form.errors}
            return render(request, "add_customer.html", {
                "form": form,
                "errors": errors,
                "post_data": request.POST
            })
    form = CustomerForm() # For GET request
    return render(request, "add_customer.html", {"form": form, "post_data": request.POST})

@role_required(["attendant", "admin"])
def customer_list(request):
    customers = Customer.objects.all()
    context = {
    'customers': customers,
    'total_customers': customers.count(),
    'on_scheme': customers.filter(on_scheme=True).count(),
    'normal_customers': customers.filter(on_scheme=False).count(),
     }
    return render(request, 'customer_list.html', context)

@role_required(["admin"])
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'add_customer.html', {'form': form})

@role_required(["admin"])
def delete_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        customer.delete()
        return redirect('customer_list')
    return render(request, 'delete_customer.html', {'customer': customer})

@role_required(["attendant", "admin"])
@transaction.atomic
def add_payment(request):
    sale_ids = request.POST.getlist('sales')

    if not sale_ids:
        sale_ids_str = request.GET.get('sales', '')
        if sale_ids_str:
            sale_ids = sale_ids_str.split(',')
        else:
            sale_ids = request.session.get('pending_sale_ids', [])

    sale_ids = [sale_id for sale_id in sale_ids if sale_id]

    sales = Sale.objects.select_related('name', 'customer_name').filter(id__in=sale_ids).order_by('id')

    if not sales:
        messages.info(request, "No pending sales found to process.")
        return redirect('sales_dash')

    payment_items = []
    subtotal_total = Decimal('0.00')
    transport_total = Decimal('0.00')
    total = Decimal('0.00')

    for sale in sales:
        line_sub_total = sale.sub_total or Decimal('0.00')
        line_transport = sale.transport or Decimal('0.00')
        line_total = sale.final_amount or Decimal('0.00')

        payment_items.append({
            'sale': sale,
            'product_name': sale.name.name if sale.name else 'Unknown Product',
            'unit_price': sale.unit_price or Decimal('0.00'),
            'quantity': sale.quantity,
            'sub_total': line_sub_total,
            'transport': line_transport,
            'line_total': line_total,
        })

        subtotal_total += line_sub_total
        transport_total += line_transport
        total += line_total

    customer = sales.first().customer_name if sales else None
    receipt_number = f"RCPT-{uuid.uuid4().hex[:8].upper()}"

    if request.method == 'POST':
        amount_given_input = request.POST.get('amount_given') or request.POST.get('amount_paid')
        if not amount_given_input:
            messages.error(request, 'Amount paid is required.')
            return render(request, 'add_payment.html', {
                'sales': sales, 'payment_items': payment_items, 'customer': customer,
                'payment_methods': Payment.PAYMENT_METHODS, 'receipt_number': receipt_number,
                'subtotal_total': subtotal_total, 'transport_total': transport_total,
                'total': total, 'amount_paid': total, 'balance': Decimal('0.00'),
            })
        try:
            amount_given = Decimal(amount_given_input)
            if amount_given < 0:
                raise ValueError
        except Exception:
            messages.error(request, 'Please enter a valid amount paid.')
            return render(request, 'add_payment.html', {
                'sales': sales, 'payment_items': payment_items, 'customer': customer,
                'payment_methods': Payment.PAYMENT_METHODS, 'receipt_number': receipt_number,
                'subtotal_total': subtotal_total, 'transport_total': transport_total,
                'total': total, 'amount_paid': total, 'balance': Decimal('0.00'),
            })
        payment_method = request.POST.get('payment_method')

        # Validate if amount_given is less than total for walk-in/unregistered customers
        # Assuming 'customer' is the customer object associated with the sale(s)
        # and that walk-in/unregistered customers might not have a full profile or are identified by a specific ID/name pattern.
        # For simplicity, if the customer is not explicitly registered (e.g., a temporary UUID customer),
        # we enforce full payment. You might need to adjust this logic based on how you identify "walk-in" customers.
        if customer and customer.name.startswith('TEMP-') and amount_given < total:
            messages.error(request, 'Walk-in customers must pay the full amount for their products.')
            return render(request, 'add_payment.html', {
                'sales': sales, 'payment_items': payment_items, 'customer': customer,
                'payment_methods': Payment.PAYMENT_METHODS, 'receipt_number': receipt_number,
                'subtotal_total': subtotal_total, 'transport_total': transport_total,
                'total': total, 'amount_paid': amount_given, 'balance': total - amount_given, # Pass back current amount_given
            })
        amount_paid = amount_given
        balance = total - amount_paid
        

        payment = Payment.objects.create(
            order_id=sales.first(),
            customer=customer,
            total=total,
            amount_paid=amount_paid,
            balance=balance,
            payment_method=payment_method,
            receipt_number=receipt_number,
            entered_by=request.user if request.user.is_authenticated else None,
        )

        # Link sales items to the payment for the receipt
        # CONNECTION: Link sales items to the payment for the itemized receipt
        sales.update(payment=payment)

        # Clear session after successful payment
        request.session.pop('pending_sale_ids', None)

        # CONNECTION: Redirect to the receipt for printing
        return redirect('payment_receipt', pk=payment.id)

    context = {
        'sales': sales,
        'payment_items': payment_items,
        'customer': customer,
        'payment_methods': Payment.PAYMENT_METHODS,
        'receipt_number': receipt_number,
        'subtotal_total': subtotal_total,
        'transport_total': transport_total,
        'total': total,
        'amount_paid': total,
        'amount_given': total,
        'balance': Decimal('0.00'),
    }

    return render(request, 'add_payment.html', context)

@role_required(["attendant", "admin"])
def payment_receipt(request, pk):
    payment = get_object_or_404(Payment, id=pk)
    sales = Sale.objects.filter(payment=payment)

    payment_items = []
    subtotal_total = Decimal('0.00')
    transport_total = Decimal('0.00')

    for sale in sales:
        sub = sale.sub_total or Decimal('0.00')
        transport = sale.transport or Decimal('0.00')
        payment_items.append({
            'product_name': sale.name.name if sale.name else 'Unknown Product',
            'unit_price': sale.unit_price or Decimal('0.00'),
            'quantity': sale.quantity,
            'sub_total': sub,
            'transport': transport,
            'line_total': sale.final_amount or Decimal('0.00'),
        })
        subtotal_total += sub
        transport_total += transport

    context = {
        'payment': payment,
        'payment_items': payment_items,
        'customer': payment.customer,
        'total': payment.total,
        'subtotal_total': subtotal_total,
        'transport_total': transport_total,
        'amount_paid': payment.amount_paid,
        'balance': max(Decimal('0.00'), payment.balance),
        'change': max(Decimal('0.00'), -payment.balance),
    }
    return render(request, 'receipt.html', context)

@role_required(["attendant", "admin"])
def payment_list(request):
    payments = Payment.objects.all().order_by('-created_at')
    total_payments = payments.count()
    total_paid = 0
    total_balance = 0

    for payment in payments:
        total_paid += payment.amount_paid
        total_balance += payment.balance

    show_sidebar = not (
        request.user.is_superuser
        or (
            hasattr(request.user, 'employee_profile')
            and request.user.employee_profile.role == 'admin'
        )
    )

    context = {

        'payments': payments,
        'total_payments': total_payments,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'show_sidebar': show_sidebar,
    }

    return render(request, 'payment_list.html', context)

@role_required(["attendant", "admin"])
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


# EXPENSE MANAGEMENT VIEWS


def generate_expense_reference():
    """Generate a unique expense reference number"""
    import datetime
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    random_str = str(uuid.uuid4())[:8].upper()
    return f"EXP-{date_str}-{random_str}"


@role_required(["admin"])
def expense_dashboard(request):
    """Display expense dashboard with summary and recent expenses"""
    
    expenses = Expense.objects.all()
    
    # Calculate statistics
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Current month
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_expenses = expenses.filter(date__gte=current_month_start).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Current year
    current_year_start = timezone.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    year_expenses = expenses.filter(date__gte=current_year_start).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Category breakdown (include percentage of total for UI)
    category_stats = []
    for category_code, category_name in Expense.EXPENSE_CATEGORIES:
        cat_total = expenses.filter(category=category_code).aggregate(Sum('amount'))['amount__sum'] or 0
        percent = 0
        try:
            if total_expenses and total_expenses != 0:
                percent = float(cat_total) / float(total_expenses) * 100
        except Exception:
            percent = 0
        category_stats.append({
            'name': category_name,
            'amount': cat_total,
            'percent': percent,
        })
    
    # Recent expenses
    recent_expenses = expenses.order_by('-date')[:10]
    
    # Payment method breakdown
    payment_methods = {}
    for method_code, method_name in Expense.PAYMENT_METHODS:
        method_total = expenses.filter(payment_method=method_code).aggregate(Sum('amount'))['amount__sum'] or 0
        payment_methods[method_name] = method_total
    
    context = {
        'total_expenses': total_expenses,
        'month_expenses': month_expenses,
        'year_expenses': year_expenses,
        'category_stats': category_stats,
        'recent_expenses': recent_expenses,
        'payment_methods': payment_methods,
    }
    
    return render(request, 'expense_dashboard.html', context)


@role_required(["admin"])
def expense_list(request):
    """Display list of all expenses with filtering and search"""
    expenses = Expense.objects.all().order_by('-date', '-created_at')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        expenses = expenses.filter(
            Q(expense_reference__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(vendor__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    # Filter by category
    category = request.GET.get('category', '')
    if category:
        expenses = expenses.filter(category=category)
    
    # Filter by payment method
    payment_method = request.GET.get('payment_method', '')
    if payment_method:
        expenses = expenses.filter(payment_method=payment_method)
    
    # Filter by date range
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    if from_date:
        expenses = expenses.filter(date__gte=from_date)
    if to_date:
        expenses = expenses.filter(date__lte=to_date)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(expenses, 20)
    page = request.GET.get('page', 1)
    expenses = paginator.get_page(page)
    
    context = {
        'expenses': expenses,
        'search_query': search_query,
        'selected_category': category,
        'selected_payment_method': payment_method,
        'from_date': from_date,
        'to_date': to_date,
        'expense_categories': Expense.EXPENSE_CATEGORIES,
        'payment_methods': Expense.PAYMENT_METHODS,
    }
    
    return render(request, 'expense_list.html', context)


@role_required(["admin"])
def add_expense(request):
    """Create a new expense record"""
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.expense_reference = generate_expense_reference()
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, f'Expense {expense.expense_reference} recorded successfully!')
            return redirect('expense_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ExpenseForm()
    
    context = {
        'form': form,
        'page_title': 'Record New Expense',
    }
    
    return render(request, 'add_expense.html', context)


@role_required(["admin"])
def edit_expense(request, pk):
    """Edit an existing expense record"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ExpenseForm(instance=expense)
    
    context = {
        'form': form,
        'expense': expense,
        'page_title': f'Edit Expense {expense.expense_reference}',
    }
    
    return render(request, 'edit_expense.html', context)


@role_required(["admin"])
def view_expense(request, pk):
    """View expense details"""
    expense = get_object_or_404(Expense, pk=pk)
    
    context = {
        'expense': expense,
    }
    
    return render(request, 'view_expense.html', context)


@role_required(["admin"])
def delete_expense(request, pk):
    """Delete an expense record"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        expense_ref = expense.expense_reference
        expense.delete()
        messages.success(request, f'Expense {expense_ref} deleted successfully!')
        return redirect('expense_list')
    
    context = {
        'expense': expense,
    }
    
    return render(request, 'delete_expense.html', context)


@role_required(["admin"])
def expense_receipt(request, pk):
    """Display printable expense receipt"""
    expense = get_object_or_404(Expense, pk=pk)
    
    context = {
        'expense': expense,
    }
    
    return render(request, 'expense_receipt.html', context)


@role_required(["admin"])
def expense_report(request):
    """Generate expense report with filters"""
    from django.db.models import Sum
    from datetime import timedelta
    
    expenses = Expense.objects.all()
    
    # Filter by date range
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    
    if not from_date:
        from_date = (timezone.now() - timedelta(days=30)).date()
    else:
        from_date = timezone.datetime.strptime(from_date, '%Y-%m-%d').date()
    
    if not to_date:
        to_date = timezone.now().date()
    else:
        to_date = timezone.datetime.strptime(to_date, '%Y-%m-%d').date()
    
    expenses = expenses.filter(date__gte=from_date, date__lte=to_date)
    
    # Category analysis
    category_analysis = []
    for category_code, category_name in Expense.EXPENSE_CATEGORIES:
        cat_expenses = expenses.filter(category=category_code)
        if cat_expenses.exists():
            cat_total = cat_expenses.aggregate(Sum('amount'))['amount__sum']
            cat_count = cat_expenses.count()
            category_analysis.append({
                'category': category_name,
                'total': cat_total,
                'count': cat_count,
                'percentage': (cat_total / (expenses.aggregate(Sum('amount'))['amount__sum'] or 1)) * 100
            })
    
    # Payment method analysis
    payment_analysis = []
    for method_code, method_name in Expense.PAYMENT_METHODS:
        method_expenses = expenses.filter(payment_method=method_code)
        if method_expenses.exists():
            method_total = method_expenses.aggregate(Sum('amount'))['amount__sum']
            method_count = method_expenses.count()
            payment_analysis.append({
                'method': method_name,
                'total': method_total,
                'count': method_count,
            })
    
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'expenses': expenses.order_by('-date'),
        'total_expenses': total_expenses,
        'category_analysis': category_analysis,
        'payment_analysis': payment_analysis,
        'from_date': from_date.isoformat(),
        'to_date': to_date.isoformat(),
    }
    
    return render(request, 'expense_report.html', context)
