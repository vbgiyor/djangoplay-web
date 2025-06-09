import random

from clients.models import Client
from core.models import ActiveManager, TimeStampedModel
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
    pdf = models.FileField(upload_to='invoices/pdfs/', blank=True, null=True)

    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-issue_date']
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"{self.invoice_number} - {self.client.name}"

    def generate_invoice_number(self):
        """Auto-generate invoice number at creation time."""
        date_str = self.issue_date.strftime("%Y%m%d")
        date_digits = list(date_str)
        random.shuffle(date_digits)
        shuffled_date = ''.join(date_digits)

        for _ in range(10):
            sequence = f"{random.randint(0, 9999):04d}"
            invoice_num = f"DJP-{shuffled_date}-{sequence}"
            if not Invoice.objects.filter(invoice_number=invoice_num).exists():
                return invoice_num
        raise ValueError("Could not generate unique invoice number after 10 attempts")

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Mark invoice as deleted with timestamp."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])


class InvoicePayment(TimeStampedModel):

    """Tracks payments against invoices."""

    id = models.AutoField(primary_key=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-paid_at']
        verbose_name = "Invoice Payment"
        verbose_name_plural = "Invoice Payments"

    def __str__(self):
        return f"Payment of {self.amount} for {self.invoice.invoice_number}"
