from django.db import migrations
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from users.models import Employee

def create_swagger_permission(apps, schema_editor):
    # Get the ContentType for the Employee model (or any model you want to associate this permission with)
    content_type = ContentType.objects.get_for_model(Employee)
    
    # Create the 'view_swagger' permission
    Permission.objects.get_or_create(
        codename='view_swagger',
        name='Can view Swagger UI',
        content_type=content_type
    )

class Migration(migrations.Migration):

    dependencies = [
        ('policyengine', '0001_initial'), 
    ]

    operations = [
        migrations.RunPython(create_swagger_permission),
    ]
