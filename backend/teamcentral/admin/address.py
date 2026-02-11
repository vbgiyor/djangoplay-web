import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from users.forms.common import AddressForm
from users.utils.helpers import user_is_verified_employee
from utilities.admin.admin_filters import AddressCityFilter, AddressCountryFilter, AddressStateFilter, AddressTypeFilter, IsActiveFilter, changelist_filter

from teamcentral.models import Address

logger = logging.getLogger(__name__)

@AdminIconDecorator.register_with_icon(Address)
class AddressAdmin(BaseAdmin):
    form = AddressForm

    list_display = (
        "owner",
        "address",
        "address_type",
        "is_active"
    )

    search_fields = (
        "owner__email",
        "address",
        "city",
    )
    actions = ['soft_delete', 'restore']

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.append("owner")
        return ro


    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        new_fieldsets = []
        for title, opts in fieldsets:
            fields = list(opts.get("fields", []))

            if obj is None:
                # ADD form → show search field only
                if "email" in fields:
                    fields.remove("email")
            else:
                # EDIT form → show read-only email only
                if "user" in fields:
                    fields.remove("user")

            new_fieldsets.append((title, {**opts, "fields": fields}))

        return new_fieldsets


    base_fieldsets_config = [
        (
            None,
            {
                "fields": (
                    "email",          # EDIT only (read-only)
                    "user",           # ADD only (Select2 search)
                    "address_type",
                    "address",
                    "country",
                    "state",
                    "city",
                    "postal_code",
                    "emergency_contact",
                    "is_active"
                )
            },
        )
    ]

    def save_model(self, request, obj, form, change):
        """
        Address Activation Rules

        ADD:
        - A newly created address is always set as active.
        - Any existing active address for the same owner is automatically
        deactivated BEFORE the new address is saved.

        EDIT:
        - If is_active=True:
            - This address is promoted to be the owner's sole active address.
            - Any other active address for the same owner is deactivated
            BEFORE saving to satisfy the database constraint.
        - If is_active=False:
            - The address is simply updated.
            - No other addresses are affected.

        Invariant:
        - At all times, an owner can have at most ONE active address.
        - Zero or more inactive addresses are allowed.
        """
        owner = obj.owner if change else form.cleaned_data.get("user")
        if not owner:
            raise ValidationError("Address must have an owner.")

        with transaction.atomic():

            # ----------------------------
            # ADD: always active
            # ----------------------------
            if not change:
                obj.owner = owner
                obj.is_active = True

                # Deactivate existing BEFORE insert
                Address.all_objects.filter(
                    owner=owner,
                    is_active=True,
                ).update(is_active=False)

                super().save_model(request, obj, form, change)
                return

            # ----------------------------
            # EDIT
            # ----------------------------
            if obj.is_active:
                # Admin wants this to be active → deactivate others FIRST
                Address.all_objects.filter(
                    owner=owner,
                    is_active=True,
                ).exclude(pk=obj.pk).update(is_active=False)

            # Now safe to save (0 or 1 active row exists)
            super().save_model(request, obj, form, change)


    @admin.display(boolean=True, description="Active")
    def is_active_display(self, obj):
        return obj.is_active

    def get_list_filter(self, request):
        base = [AddressTypeFilter, IsActiveFilter, AddressCountryFilter,
                AddressStateFilter, AddressCityFilter,
                changelist_filter("owner")]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=Address))
        return base
