from django.apps import apps
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = """Backfill initial '+' historical records for django-simple-history.

    Usage examples:
        ./manage.py backfill_history
        ./manage.py backfill_history --app locations
        ./manage.py backfill_history --model locations.CustomCity
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--app', type=str, help='App label to process all models in that app'
        )
        parser.add_argument(
            '--model', type=str, help='Full model name (app_label.ModelName) to process only that model'
        )
        parser.add_argument(
            '--batch-size', type=int, default=1000, help='Number of objects per bulk insert'
        )
        parser.add_argument(
            '--dry-run', action='store_true', help='Simulate the backfill without writing changes'
        )


    def handle(self, *args, **options):
        app_label = options.get('app')
        model_name = options.get('model')
        batch_size = options.get('batch_size')

        # Determine models to process
        models_to_process = []

        if model_name:
            try:
                model = apps.get_model(model_name)
                models_to_process.append(model)
            except LookupError:
                self.stderr.write(self.style.ERROR(f"Model '{model_name}' not found."))
                return
        elif app_label:
            models = apps.get_app_config(app_label).get_models()
            models_to_process.extend(models)
        else:
            models_to_process = apps.get_models()

        total_models = 0
        total_backfilled = 0

        self.stdout.write(self.style.MIGRATE_HEADING("Starting history backfill..."))

        for model in models_to_process:
            if not model._meta.managed or model._meta.proxy:
                continue

            history_manager = getattr(model, "history", None)
            if history_manager is None:
                continue

            total_models += 1
            model_label = f"{model._meta.app_label}.{model.__name__}"
            qs = model.objects.all()
            count_objects = qs.count()
            count_backfilled = 0
            self.stdout.write(f"\nChecking {model_label} ({count_objects} objects)...")

            historical_model = model.history.model
            field_names = [f.name for f in model._meta.fields]

            rows_to_create = []

            for idx, obj in enumerate(qs, start=1):
                if obj.history.count() == 0:
                    # Pick a timestamp from typical "created" fields
                    dt = None
                    for field in ["created_at", "created", "created_on", "timestamp", "created_date"]:
                        if hasattr(obj, field):
                            dt = getattr(obj, field)
                            break
                    if dt is None:
                        dt = timezone.now()

                    rows_to_create.append(
                        historical_model(
                            # **{f: getattr(obj, f) for f in field_names},
                            **{f: getattr(obj, f) for f in field_names if f in [field.name for field in historical_model._meta.fields]},
                            history_type="+",
                            history_date=dt
                        )
                    )
                    count_backfilled += 1

                # Bulk insert when batch_size reached
                if len(rows_to_create) >= batch_size:
                    if not options['dry_run']:
                        historical_model.objects.bulk_create(rows_to_create)
                    rows_to_create = []
                    self.stdout.write(f"  → {idx}/{count_objects} processed...")

            # Insert remaining rows
            if rows_to_create:
                if not options['dry_run']:
                    historical_model.objects.bulk_create(rows_to_create)


            total_backfilled += count_backfilled
            if count_backfilled:
                self.stdout.write(self.style.SUCCESS(f"  → Added {count_backfilled} missing history rows."))
            else:
                self.stdout.write("  → No missing history rows.")

            if options['dry_run']:
                self.stdout.write(self.style.WARNING("Dry-run enabled: No data was written."))

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nBackfill complete: {total_backfilled} total records created across {total_models} models."
        ))
