from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from adminapp.forms import SupplierForm
from adminapp.models import DepositPayment, DepositScheme
from nyondoapp.models import Customer, Product


class SupplierFormValidationTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Nails",
            description="Box of nails",
            specification="50mm",
            stock_quantity=50,
            type="Hardware",
            cost_price=Decimal("300.00"),
            unit_price=Decimal("500.00"),
            reorder_level=10,
            entered_by=None,
        )

    def test_supplier_contact_is_required(self):
        form = SupplierForm(
            data={
                "name": "Apex Suppliers",
                "category": "Hardware",
                "address": "Kampala",
                "contact": "",
                "email": "apex@example.com",
                "outstanding_credit": 0,
                "amount_paid": 0,
                "status": "Pending",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("contact", form.errors)

    def test_supplier_contact_must_be_valid_ugandan_number(self):
        form = SupplierForm(
            data={
                "name": "Apex Suppliers",
                "category": "Hardware",
                "address": "Kampala",
                "contact": "12345",
                "email": "apex@example.com",
                "outstanding_credit": 0,
                "amount_paid": 0,
                "status": "Pending",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("contact", form.errors)


class DepositSchemeEditTests(TestCase):
    def test_edit_deposit_recalculates_amounts(self):
        product = Product.objects.create(
            name="Drill",
            description="Electric drill",
            specification="18V",
            stock_quantity=5,
            type="Tool",
            cost_price=Decimal("8000.00"),
            unit_price=Decimal("12000.00"),
            reorder_level=2,
            entered_by=None,
        )
        customer = Customer.objects.create(
            name="Jane Doe",
            on_scheme=True,
            phone="0770123456",
            nin="12345678901234",
            other_details="Deposit customer",
        )
        deposit = DepositScheme.objects.create(
            customer=customer,
            product=product,
            total_amount=Decimal("12000.00"),
            amount_paid=Decimal("2000.00"),
            balance=Decimal("10000.00"),
            quantity_expected=1,
        )

        response = self.client.post(
            reverse("edit_deposit", args=[deposit.pk]),
            data={"quantity_expected": 2},
        )

        self.assertRedirects(response, reverse("deposit_list"))
        deposit.refresh_from_db()
        self.assertEqual(deposit.quantity_expected, 2)
        self.assertEqual(deposit.total_amount, Decimal("24000.00"))
        self.assertEqual(deposit.balance, Decimal("22000.00"))

    def test_unpaid_deposit_list_shows_pending_with_balance(self):
        product = Product.objects.create(
            name="Cement",
            description="Bag cement",
            specification="50kg",
            stock_quantity=20,
            type="Building",
            cost_price=Decimal("25000.00"),
            unit_price=Decimal("35000.00"),
            reorder_level=5,
            entered_by=None,
        )
        customer = Customer.objects.create(
            name="Sarah",
            on_scheme=True,
            phone="0770123456",
            nin="98765432101234",
            other_details="Deposit customer",
        )
        deposit = DepositScheme.objects.create(
            customer=customer,
            product=product,
            quantity_expected=2,
            amount_paid=Decimal("0.00"),
        )

        response = self.client.get(reverse("deposit_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending")
        self.assertContains(response, "70,000")
        deposit.refresh_from_db()
        self.assertEqual(deposit.status, "Pending")

    def test_add_deposit_opening_amount_creates_payment_record(self):
        product = Product.objects.create(
            name="Paint",
            description="Interior paint",
            specification="20L",
            stock_quantity=12,
            type="Paint",
            cost_price=Decimal("60000.00"),
            unit_price=Decimal("90000.00"),
            reorder_level=3,
            entered_by=None,
        )
        customer = Customer.objects.create(
            name="Isaac",
            on_scheme=True,
            phone="0770123456",
            nin="22345678901234",
            other_details="Deposit customer",
        )

        response = self.client.post(
            reverse("add_deposit"),
            data={
                "customer": customer.pk,
                "product": product.pk,
                "quantity_expected": "2",
                "amount_paid": "50000.00",
                "payment_method": "cash",
            },
        )

        self.assertRedirects(response, reverse("deposit_dashboard"))
        deposit = DepositScheme.objects.get(customer=customer)
        self.assertEqual(deposit.total_amount, Decimal("180000.00"))
        self.assertEqual(deposit.amount_paid, Decimal("50000.00"))
        self.assertEqual(deposit.balance, Decimal("130000.00"))
        self.assertEqual(deposit.status, "Active")
        self.assertEqual(DepositPayment.objects.filter(scheme=deposit).count(), 1)
