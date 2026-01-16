import re

from django import forms
from users.models.support import SupportTicket


class BugReportForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    subject = forms.CharField(max_length=200, required=False)
    message = forms.CharField(widget=forms.Textarea, required=True)
    github_issue = forms.URLField(required=False)

    class Meta:
        model = SupportTicket
        fields = ['email', 'subject', 'message', 'github_issue']

    def enforce_logged_in_email(self, request):
        if request.user.is_authenticated:
            self.fields['email'].initial = request.user.email
            self.fields['email'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        files = self.files.getlist('files')
        if files:
            if len(files) > 5:
                raise forms.ValidationError("Maximum 5 files allowed.")
            for f in files:
                if f.size > 10 * 1024 * 1024:
                    raise forms.ValidationError(f"'{f.name}' exceeds 10MB limit.")
        return cleaned_data

    def clean_github_issue(self):
        url = self.cleaned_data.get('github_issue')
        if url:
            pattern = r'^https://github\.com/[^/]+/[^/]+/issues/\d+$'
            if not re.match(pattern, url):
                raise forms.ValidationError("Enter a valid GitHub issue URL.")
        return url
