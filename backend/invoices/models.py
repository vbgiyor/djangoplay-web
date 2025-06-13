import random

from clients.models import Client
from core.models import ActiveManager, TimeStampedModel
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class InvoiceStatus(models.Model):

    """Represents the status of an invoice (e.g., Draft, Paid)."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    code = models.SlugField(
        max_length=50,
        unique=True,
        help_text="e.g., 'draft', 'sent', 'paid'"
    )
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Invoice Status"
        verbose_name_plural = "Invoice Statuses"
        ordering = ['id']

    def __str__(self):
        return self.name

    def is_closed(self):
        """Return True if the status indicates the invoice is closed (e.g., paid or cancelled)."""
        return self.code.lower() in ['paid', 'cancelled']


class PaymentMethod(models.Model):

    """Represents a payment method (e.g., UPI, credit card)."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    code = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Short code for internal use (e.g., 'credit_card', 'upi')"
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
        ordering = ['id']

    def __str__(self):
        return self.name


class Invoice(TimeStampedModel):

    """Model for client invoices with detailed metadata."""

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.ForeignKey(
        InvoiceStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    docs = models.FileField(upload_to='invoices/docs/', blank=True, null=True)

    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-issue_date']
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        indexes = [
            models.Index(fields=['due_date']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.client.name}"

    def generate_invoice_number(self):
        """Generate a unique invoice number in the format: DJP-{random_6_digit_number}-XXXXXX."""
        max_attempts = 1000000  # Maximum attempts to find a unique invoice number
        for i in range(1, max_attempts + 1):
            random_prefix = random.randint(100000, 999999)  # Generate a random 6-digit number
            invoice_num = f"DJP-{random_prefix}-{i:06d}"
            if not Invoice.objects.filter(invoice_number=invoice_num).exists():
                return invoice_num
        raise ValueError("Could not generate unique invoice number after multiple attempts.")

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Mark invoice as deleted with timestamp."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def clean(self):
        """Validate due_date >= issue_date and non-negative amount."""
        if self.due_date < self.issue_date:
            raise ValidationError("Due date must be on or after issue date.")
        if self.amount < 0:
            raise ValidationError("Amount cannot be negative.")

    @property
    def remaining_amount(self):
        """Calculate outstanding balance."""
        paid = sum(payment.amount for payment in self.payments.filter(deleted_at__isnull=True))
        return self.amount - paid

    @property
    def is_overdue(self):
        """Determine if the invoice is overdue based on due_date, remaining amount, and status."""
        if self.deleted_at:  # Soft-deleted invoices are not overdue
            return False
        if self.remaining_amount <= 0:  # Fully paid invoices are not overdue
            return False
        if self.status and self.status.is_closed():
            return False
        return self.due_date < timezone.now().date()  # Due date has passed


class InvoicePayment(TimeStampedModel):

    """Tracks payments against invoices."""

    id = models.AutoField(primary_key=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-paid_at']
        verbose_name = "Invoice Payment"
        verbose_name_plural = "Invoice Payments"

    def __str__(self):
        return f"Payment of {self.amount} for {self.invoice.invoice_number}"

    def generate_reference(self):
        """Generate reference in format: first 4 letters of payment method + client_id + DDMM + last 4 digits of invoice number."""
        if not self.method or not self.invoice:
            raise ValueError("Payment method and invoice are required to generate reference.")

        method_prefix = (self.method.name[:4].upper() if len(self.method.name) >= 4 else self.method.name.upper().ljust(4, '0'))
        client_id = str(self.invoice.client.id)
        invoice_suffix = self.invoice.invoice_number[-4:]

        return f"{method_prefix}{client_id}{random.randint(0, 4)}{invoice_suffix}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        if not self.paid_at:
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate non-negative payment amount and total payments not exceeding invoice amount."""
        if self.amount < 0:
            raise ValidationError("Payment amount cannot be negative.")
        total_payments = sum(payment.amount for payment in self.invoice.payments.filter(deleted_at__isnull=True))
        if total_payments + self.amount > self.invoice.amount:
            raise ValidationError("Total payments cannot exceed invoice amount.")
