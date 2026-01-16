from django.db import migrations


def deactivate_orphan_active_addresses(apps, schema_editor):
    Address = apps.get_model("users", "Address")

    # Deactivate orphan addresses that are still marked active
    Address.objects.filter(
        owner__isnull=True,
        is_active=True,
    ).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0017_backfill_address_owner_and_text"),
    ]

    operations = [
        migrations.RunPython(deactivate_orphan_active_addresses),
    ]
