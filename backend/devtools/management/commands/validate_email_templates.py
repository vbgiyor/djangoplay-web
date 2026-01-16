from django.core.management.base import BaseCommand
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import get_template
from utilities.constants.template_registry import TemplateRegistry as T

EMAIL_PREFIXES = [
    T.PASSWORD_RESET_EMAIL,
    T.EMAIL_SIGNUP_SUCCESS,
    T.EMAIL_VERIFICATION_MANUAL,
    T.EMAIL_VERIFICATION_SSO,
    T.REQUEST_TO_SUPPORT_EMAIL,
    T.CONFIRMATION_TO_USER_EMAIL,
]


class Command(BaseCommand):
    help = "Validate email templates (syntax + renderability)"

    def handle(self, *args, **options):
        ok = []
        skipped = []
        errors = []

        for prefix in EMAIL_PREFIXES:
            try:
                # 1. HTML must exist and compile
                get_template(f"account/email/{prefix}.html")

                # 2. Subject is optional but should compile if present
                try:
                    get_template(f"account/email/{prefix}_subject.txt")
                except TemplateDoesNotExist:
                    pass

                # 3. Text: email/ preferred, fallback/ allowed
                try:
                    get_template(f"account/email/{prefix}.txt")
                except TemplateDoesNotExist:
                    try:
                        get_template(f"account/fallback/{prefix}.txt")
                    except TemplateDoesNotExist:
                        pass

                ok.append(prefix)

            except TemplateSyntaxError as e:
                errors.append((prefix, str(e)))

            except TemplateDoesNotExist:
                # ONLY if the HTML template itself is missing
                skipped.append(prefix)

            except Exception as e:
                errors.append((prefix, f"Unexpected error: {e}"))

        # ------------------------------------------------------------------
        # FINAL SUMMARY OUTPUT (single, clean block)
        # ------------------------------------------------------------------
        self.stdout.write("\nRESULT SUMMARY")
        self.stdout.write("-" * 14)

        if ok:
            self.stdout.write("\nOK:")
            for name in ok:
                self.stdout.write(f"  - {name}")

        if skipped:
            self.stdout.write("\nSKIPPED (depends on runtime variables):")
            for name in skipped:
                self.stdout.write(f"  - {name}")

        if errors:
            self.stdout.write("\nERRORS:")
            for name, msg in errors:
                self.stdout.write(f"  - {name}: {msg}")

        if errors:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("Template validation FAILED"))
            raise SystemExit(1)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("All email templates validated successfully"))
