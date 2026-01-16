import logging

from django import forms
from industries.models import Industry

logger = logging.getLogger(__name__)


class IndustryForm(forms.ModelForm):

    """
    Form for creating/updating Industry instances.

    - Excludes system-managed / audit fields
    - Delegates validation to ModelForm + Industry.clean()
    - Passes `user` through to Industry.save(user=...) so audit fields work
    """

    class Meta:
        model = Industry
        # Explicitly exclude fields that are auto/managed by system
        exclude = (
            "id",
            "deleted_at",
            "deleted_by",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "history",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        """
        Optionally accept `user` and store it for use in save():
        form = IndustryForm(request.POST, user=request.user)
        """
        self._user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        logger.debug(
            "Initialized IndustryForm for instance=%s (user=%s)",
            getattr(self.instance, "pk", None),
            self._user,
        )

    def clean(self):
        """
        Hook into form-wide validation.

        - Calls parent clean() which in turn:
          * Validates individual fields
          * Calls Industry.clean() (model-level validation)
        - Logs validation outcome.
        """
        logger.debug("IndustryForm.clean() called")
        cleaned_data = super().clean()

        if self.errors:
            logger.warning(
                "IndustryForm validation errors for instance=%s: %s",
                getattr(self.instance, "pk", None),
                self.errors.as_json(),
            )
        else:
            logger.info(
                "IndustryForm validated successfully for instance=%s",
                getattr(self.instance, "pk", None),
            )

        return cleaned_data

    def save(self, commit=True, user=None):
        """
        Save the Industry instance.

        - Uses `user` argument if provided, otherwise falls back to `self._user`.
        - Ensures Industry.save(user=...) is called so audit fields are set.
        """
        effective_user = user or self._user

        logger.info(
            "IndustryForm.save() called for instance=%s (commit=%s, user=%s)",
            getattr(self.instance, "pk", None),
            commit,
            effective_user,
        )

        # First let ModelForm construct/update the instance without saving to DB
        instance = super().save(commit=False)

        if commit:
            # Call model.save(user=...) so your custom audit logic runs
            logger.debug(
                "Calling Industry.save(user=...) for instance=%s",
                getattr(instance, "pk", None),
            )
            instance.save(user=effective_user)

            # Handle many-to-many fields after the instance has a PK
            self.save_m2m()
            logger.info(
                "Industry instance saved (pk=%s, code=%s)",
                instance.pk,
                instance.code,
            )
        else:
            logger.debug(
                "IndustryForm.save() called with commit=False; instance not saved to DB"
            )

        return instance
