# yourapp/management/commands/backfill_history.py
import logging
import sys
import time
from datetime import datetime
from typing import Iterable, Iterator, List, Optional, Set

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

# Try to use your project's spinner helper if available; otherwise use a simple fallback.
try:
    from core.utils.cmd_status import animate_processing  # optional existing spinner
except Exception:
    animate_processing = None

logger = logging.getLogger(__name__)


def _simple_spinner(stop_event, out=sys.stdout, interval=0.12):
    """Simple spinner fallback. stop_event is a threading.Event()-like object with is_set()."""
    import itertools
    chars = itertools.cycle("|/-\\")
    while not stop_event.is_set():
        out.write(next(chars))
        out.flush()
        time.sleep(interval)
        out.write("\b")


class Command(BaseCommand):
    help = (
        "Backfill initial '+' historical records for django-simple-history.\n\n"
        "Examples:\n"
        "  ./manage.py backfill_history\n"
        "  ./manage.py backfill_history --app locations\n"
        "  ./manage.py backfill_history --model locations.CustomCity --batch-size 50000\n"
        "  ./manage.py backfill_history --model locations.CustomCity --dry-run\n"
    )

    def add_arguments(self, parser):
        parser.add_argument("--app", type=str, help="App label to process all models in that app")
        parser.add_argument("--model", type=str, help="Full model name (app_label.ModelName) to process only that model")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Number of history rows to create per bulk_create (default: 5000)",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=50000,
            help="Query iterator chunk size when scanning model objects (default: 2000)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Simulate the backfill (no DB writes)")
        parser.add_argument("--start-pk", type=int, help="Start processing at this PK (inclusive)")
        parser.add_argument("--end-pk", type=int, help="Stop processing at this PK (inclusive)")
        parser.add_argument("--resume", action="store_true", help="Attempt to resume using start-pk where you left off")
        parser.add_argument(
            "--preload-threshold",
            type=int,
            default=1_000_000,
            help="If model count <= threshold, preload existing history PKs into memory for speed (default 1_000_000).",
        )

    def _iter_model_objects(self, model, start_pk: Optional[int], end_pk: Optional[int], chunk_size: int) -> Iterator:
        qs = model.objects.all().order_by(model._meta.pk.name)
        if start_pk is not None:
            qs = qs.filter(**{f"{model._meta.pk.name}__gte": start_pk})
        if end_pk is not None:
            qs = qs.filter(**{f"{model._meta.pk.name}__lte": end_pk})
        # Use iterator to avoid caching whole queryset
        return qs.iterator(chunk_size=chunk_size)

    def _chunked(self, iterable: Iterable, n: int) -> Iterator[List]:
        chunk = []
        for item in iterable:
            chunk.append(item)
            if len(chunk) >= n:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def _get_existing_history_pks_preload(self, historical_model, pk_field_name: str) -> Set:
        """Load distinct original-object PKs that already have history entries."""
        qs = historical_model.objects.values_list(pk_field_name, flat=True).distinct()
        return set(qs)

    def _get_existing_history_pks_batch(self, historical_model, pks: List, pk_field_name: str) -> Set:
        return set(historical_model.objects.filter(**{f"{pk_field_name}__in": pks}).values_list(pk_field_name, flat=True))

    def _create_history_instances(
        self,
        model,
        historical_model,
        objs: List,
        field_names: List[str],
        default_dt: Optional[datetime],
    ) -> List:
        rows = []
        for obj in objs:
            # Compose kwargs for historical model using model fields' names; fall back to None on error
            kwargs = {}
            # Fields that are often added by third-party apps (like django-mptt) but might not be present on historical models
            # and cause TypeError during instantiation.
            for f in field_names:
                try:
                    kwargs[f] = getattr(obj, f)
                except Exception:
                    kwargs[f] = None
            # history_type '+' indicates creation
            rows.append(
                historical_model(
                    **kwargs,
                    history_type="+",
                    history_date=getattr(obj, "created_at", default_dt or timezone.now()),
                )
            )
        return rows

    def handle(self, *args, **options):
        app_label = options.get("app")
        model_name = options.get("model")
        batch_size = int(options.get("batch_size") or 5000)
        chunk_size = int(options.get("chunk_size") or 2000)
        dry_run = bool(options.get("dry_run"))
        start_pk = options.get("start_pk")
        end_pk = options.get("end_pk")
        bool(options.get("resume"))
        preload_threshold = int(options.get("preload_threshold") or 1_000_000)

        # Determine models to process
        models_to_process = []
        if model_name:
            try:
                models_to_process.append(apps.get_model(model_name))
            except LookupError:
                raise CommandError(f"Model '{model_name}' not found.")
        elif app_label:
            try:
                models_to_process.extend(list(apps.get_app_config(app_label).get_models()))
            except LookupError:
                raise CommandError(f"App '{app_label}' not found.")
        else:
            models_to_process = list(apps.get_models())

        # short-circuit
        if not models_to_process:
            self.stdout.write(self.style.WARNING("No models found to process."))
            return

        total_models = 0
        total_backfilled = 0
        start_time = time.time()

        self.stdout.write(self.style.MIGRATE_HEADING("Starting history backfill..."))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: No changes will be written to the database."))

        for model in models_to_process:
            # skip unmanaged or proxy models
            if not model._meta.managed or model._meta.proxy:
                continue

            history_manager = getattr(model, "history", None)
            if history_manager is None:
                continue

            total_models += 1
            model_label = f"{model._meta.app_label}.{model.__name__}"
            qs_total = model.objects.all()
            if start_pk is not None or end_pk is not None:
                # count with bounds
                count_objects = qs_total.filter(
                    **({f"{model._meta.pk.name}__gte": start_pk} if start_pk is not None else {}),
                    **({f"{model._meta.pk.name}__lte": end_pk} if end_pk is not None else {}),
                ).count()
            else:
                # count once (may be expensive for very large tables)
                try:
                    count_objects = qs_total.count()
                except Exception:
                    count_objects = None

            self.stdout.write(f"\nChecking {model_label} ({'?' if count_objects is None else count_objects} objects)...")

            historical_model = model.history.model
            field_names = [f.name for f in model._meta.fields]
            pk_field_name = model._meta.pk.name

            # Optionally preload existing history pks if dataset size is reasonable
            existing_history_pks = None
            if count_objects is not None and count_objects <= preload_threshold:
                try:
                    self.stdout.write(self.style.NOTICE("Preloading set of object PKs that already have history (fast path)..."))
                    existing_history_pks = self._get_existing_history_pks_preload(historical_model, pk_field_name)
                    logger.debug("Preloaded %d existing history pks for %s", len(existing_history_pks), model_label)
                except Exception as e:
                    logger.warning("Preload failed for %s: %s (falling back to batch checks)", model_label, e)
                    existing_history_pks = None

            backfilled_for_model = 0
            rows_to_create = []

            # iterate in PK order to be deterministic and allow resume via start_pk
            iter_objs = self._iter_model_objects(model, start_pk, end_pk, chunk_size)

            processed = 0
            last_pk = None

            # We'll process in chunks to check history existence per chunk (avoid per-object queries)
            for chunk in self._chunked(iter_objs, chunk_size):
                processed += len(chunk)
                chunk_pks = [getattr(o, pk_field_name) for o in chunk]

                # Determine which pks already have history within this chunk
                if existing_history_pks is not None:
                    have_history_pks = {pk for pk in chunk_pks if pk in existing_history_pks}
                else:
                    # query historical_model for this batch of pks
                    have_history_pks = self._get_existing_history_pks_batch(historical_model, chunk_pks, pk_field_name)

                # Build list of objs missing history
                missing_objs = [o for o in chunk if getattr(o, pk_field_name) not in have_history_pks]

                # Create historical_model instances for missing objects (use obj.created_at if present)
                if missing_objs:
                    # Default timestamp for rows in this chunk
                    default_dt = timezone.now()
                    prepared = self._create_history_instances(model, historical_model, missing_objs, field_names, default_dt)
                    rows_to_create.extend(prepared)
                    backfilled_for_model += len(prepared)

                    # When rows_to_create reached batch_size -> bulk_create them
                    if len(rows_to_create) >= batch_size:
                        if dry_run:
                            self.stdout.write(self.style.WARNING(f"[DRY] Would bulk_create {len(rows_to_create)} rows (processed {processed})."))
                        else:
                            # use smaller transactions for safety
                            try:
                                with transaction.atomic():
                                    historical_model.objects.bulk_create(rows_to_create)
                            except Exception as e:
                                logger.exception("bulk_create failed for model %s: %s", model_label, e)
                                raise
                        rows_to_create = []

                # progress reporting
                last_pk = chunk_pks[-1]
                if count_objects:
                    (processed / count_objects) * 100 if count_objects else None
                    self.stdout.write(self.style.NOTICE(f"  → processed {processed}/{count_objects} (last_pk={last_pk})"))
                else:
                    self.stdout.write(self.style.NOTICE(f"  → processed {processed} (last_pk={last_pk})"))

            # final flush
            if rows_to_create:
                if dry_run:
                    self.stdout.write(self.style.WARNING(f"[DRY] Would bulk_create final {len(rows_to_create)} rows for {model_label}."))
                else:
                    try:
                        with transaction.atomic():
                            historical_model.objects.bulk_create(rows_to_create)
                    except Exception as e:
                        logger.exception("Final bulk_create failed for model %s: %s", model_label, e)
                        raise

            total_backfilled += backfilled_for_model
            self.stdout.write(self.style.SUCCESS(f"  → Added {backfilled_for_model} missing history rows for {model_label}."))

        elapsed = time.time() - start_time
        self.stdout.write(self.style.MIGRATE_HEADING(f"\nBackfill complete: {total_backfilled} total records created across {total_models} models in {elapsed:.1f}s."))
