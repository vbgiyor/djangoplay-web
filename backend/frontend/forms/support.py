from django import forms
from django.utils.translation import gettext as _


class SupportForm(forms.Form):
    subject = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5})
    )

    def clean(self):
        cleaned_data = super().clean()
        files = self.files.getlist("files")
        if files:
            if len(files) > 5:
                raise forms.ValidationError(_("Maximum 5 files allowed."))
            for f in files:
                if f.size > 10 * 1024 * 1024:
                    raise forms.ValidationError(_("Each file must be ≤10MB."))
        return cleaned_data

    def enforce_logged_in_email(self, request):
        """
        If the user is logged in, pin the email field to their account email
        and make it read-only.
        """
        if request.user.is_authenticated:
            self.fields["email"].initial = request.user.email
            self.fields["email"].widget.attrs["readonly"] = True
            self.fields["name"].initial = request.user.username
            self.fields["name"].widget.attrs["readonly"] = True
