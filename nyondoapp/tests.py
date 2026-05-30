from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from adminapp.models import Supplier
from .forms import CustomerForm
from .models import Customer, Product, Sale, Stock


class CustomerFormValidationTests(TestCase):
    def test_valid_ugandan_phone_and_nin_pass(self):
        form = CustomerForm(
            data={
                "name": "Priscilla Veronika",
                "on_scheme": False,
                "phone": "+256770123456",
                "nin": "CM123456789ABC",
                "other_details": "Preferred evening calls",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_ugandan_phone_rejected(self):
        form = CustomerForm(
            data={
                "name": "Patricia Josephine",
                "on_scheme": False,
                "phone": "12345",
                "nin": "12345678901234",
                "other_details": "Preferred evening calls",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

class CustomerViewTests(TestCase):
    def test_add_customer_returns_validation_errors(self):
        response = self.client.post(
            reverse("add_customer"),
            data={
                "name": "Daughter",
                "on_scheme": False,
                "phone": "12345",
                "nin": "ABC123",
                "other_details": "Preferred evening calls",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid Ugandan mobile number")
        self.assertContains(response, "Enter a valid 14-character alphanumeric NIN")

    def test_customer_edit_updates_existing_record(self):
        customer = Customer.objects.create(
            name="Original Name",
            on_scheme=False,
            phone="0770123456",
            nin="12345678901234",
            other_details="Original details",
        )

        response = self.client.post(
            reverse("customer_edit", args=[customer.pk]),
            data={
                "name": "Updated Name",
                "on_scheme": True,
                "phone": "0780123456",
                "nin": "12345678901234",
                "other_details": "Updated details",
            },
        )

        self.assertRedirects(response, reverse("customer_list"))
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Updated Name")
        self.assertTrue(customer.on_scheme)
        self.assertEqual(customer.phone, "0780123456")


class StockViewTests(TestCase):
    def test_add_stock_accepts_decimal_prices(self):
        user = get_user_model().objects.create_user(
            username="stockkeeper",
            password="pass1234",
        )
        product = Product.objects.create(
            name="Cable",
            description="Electrical cable",
            specification="3m",
            stock_quantity=10,
            type="Electrical",
            cost_price=Decimal("10000.00"),
            unit_price=Decimal("12000.00"),
            reorder_level=5,
            entered_by=user,
        )
        supplier = Supplier.objects.create(
            name="Power Supply Co",
            product=product,
            category="Electrical",
            address="Kampala",
            contact="0770123456",
            email="power@example.com",
            outstanding_credit=Decimal("0.00"),
            amount_paid=Decimal("0.00"),
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse("add_stock"),
            data={
                "product": product.pk,
                "supplier": supplier.pk,
                "quantity": "100",
                "cost_price": "20000.00",
                "unit_price": "23000.00",
                "total_cost": "2000000.00",
                "is_paid": "on",
                "comments": "Bulk order",
            },
        )

        self.assertRedirects(response, reverse("stock"))
        product.refresh_from_db()
        stock = Stock.objects.get(product=product, supplier=supplier)

        self.assertEqual(product.cost_price, Decimal("20000.00"))
        self.assertEqual(product.unit_price, Decimal("23000.00"))
        self.assertEqual(product.stock_quantity, 110)
        self.assertEqual(stock.quantity, 100)
        self.assertEqual(stock.total_cost, Decimal("2000000.00"))


class SaleAndPaymentFlowTests(TestCase):
    def test_add_sales_creates_multiple_items_and_reduces_stock(self):
        customer = Customer.objects.create(
            name="Noreen",
            on_scheme=False,
            phone="0770123456",
            nin="12345678901234",
            other_details="Walk-in",
        )
        user = get_user_model().objects.create_user(
            username="salesclerk",
            password="pass1234",
        )
        product_one = Product.objects.create(
            name="Drill",
            description="Power drill",
            specification="18V",
            stock_quantity=10,
            type="Tool",
            cost_price=Decimal("5000.00"),
            unit_price=Decimal("7000.00"),
            reorder_level=3,
            entered_by=user,
        )
        product_two = Product.objects.create(
            name="Hammer",
            description="Claw hammer",
            specification="Medium",
            stock_quantity=5,
            type="Tool",
            cost_price=Decimal("3000.00"),
            unit_price=Decimal("4500.00"),
            reorder_level=2,
            entered_by=user,
        )

        response = self.client.post(
            reverse("add_sales"),
            data={
                "customer_name": customer.pk,
                "distance": "5",
                "payment_method": "cash",
                "comments": "Mixed sale",
                "product": [product_one.pk, product_two.pk],
                "quantity": ["2", "1"],
            },
        )

        self.assertRedirects(response, reverse("add_payment"))
        self.assertEqual(Sale.objects.count(), 2)
        product_one.refresh_from_db()
        product_two.refresh_from_db()
        self.assertEqual(product_one.stock_quantity, 8)
        self.assertEqual(product_two.stock_quantity, 4)

    def test_add_payment_uses_receipt_total_and_shows_items_on_receipt(self):
        customer = Customer.objects.create(
            name="Moses",
            on_scheme=False,
            phone="0771123456",
            nin="22345678901234",
            other_details="Bulk buyer",
        )
        user = get_user_model().objects.create_user(
            username="cashier",
            password="pass1234",
        )
        product = Product.objects.create(
            name="Paint",
            description="Exterior paint",
            specification="5L",
            stock_quantity=10,
            type="Paint",
            cost_price=Decimal("1000.00"),
            unit_price=Decimal("1500.00"),
            reorder_level=2,
            entered_by=user,
        )

        sale_one = Sale.objects.create(
            name=product,
            quantity=2,
            distance=0,
            transport=0,
            sub_total=Decimal("3000.00"),
            customer_name=customer,
            final_amount=Decimal("3000.00"),
            payment_method="cash",
            comments="Paint order",
            recorded_by=user,
            receipt_number="RCPT-TEST-1",
        )
        sale_two = Sale.objects.create(
            name=product,
            quantity=1,
            distance=0,
            transport=0,
            sub_total=Decimal("1500.00"),
            customer_name=customer,
            final_amount=Decimal("1500.00"),
            payment_method="cash",
            comments="Paint order",
            recorded_by=user,
            receipt_number="RCPT-TEST-2",
        )

        response = self.client.post(
            reverse("add_payment"),
            data={
                "sales": [sale_one.pk, sale_two.pk],
                "amount_paid": "4500.00",
                "payment_method": "cash",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paint")
        self.assertContains(response, "4,500")
        self.assertEqual(response.context["payment"].total, Decimal("4500.00"))
        self.assertEqual(response.context["payment"].balance, Decimal("0.00"))
        self.assertEqual(response.context["sales"][0].id, sale_one.id)
        self.assertEqual(response.context["sales"][1].id, sale_two.id)

    def test_add_payment_displays_itemized_sales_table(self):
        customer = Customer.objects.create(
            name="Moses",
            on_scheme=False,
            phone="0771123456",
            nin="22345678901234",
            other_details="Bulk buyer",
        )
        user = get_user_model().objects.create_user(
            username="cashier",
            password="pass1234",
        )
        product = Product.objects.create(
            name="Paint",
            description="Exterior paint",
            specification="5L",
            stock_quantity=10,
            type="Paint",
            cost_price=Decimal("1000.00"),
            unit_price=Decimal("1500.00"),
            reorder_level=2,
            entered_by=user,
        )

        sale = Sale.objects.create(
            name=product,
            quantity=2,
            distance=0,
            transport=0,
            sub_total=Decimal("3000.00"),
            customer_name=customer,
            final_amount=Decimal("3000.00"),
            payment_method="cash",
            comments="Paint order",
            recorded_by=user,
            receipt_number="RCPT-TEST-3",
        )

        response = self.client.get(reverse("add_payment"), {"sales": sale.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unit Price")
        self.assertContains(response, "Line Total")
        self.assertContains(response, "Transport")
        self.assertContains(response, "Paint")
        self.assertContains(response, "3,000")
