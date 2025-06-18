from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def add_user_to_group(sender, instance, created, **kwargs):
    # Based on the role, add user to related group

    if created:
        if instance.role == 'ADMINISTRATOR':
            admin_group, _ = Group.objects.get_or_create(name='Administrator')
            instance.groups.add(admin_group)
        if instance.role == 'MANAGER':
            manager_group, _ = Group.objects.get_or_creat(name='Manager')
            instance.groups.add(manager_group)
        if instance.role == 'ACCOUNTANT':
            accountant_group, _, = Group.objects.get_or_create(name='Accountant')
            instance.groups.add(accountant_group)
        if instance.role == 'AUDITOR':
            audit_group, _, = Group.objects.get_or_create(name='Auditor')
            instance.groups.add(audit_group)
        if instance.role == 'CLERK':
            clerk_group, _, = Group.objects.get_or_create(name='Clerk')
            instance.groups.add(clerk_group)
