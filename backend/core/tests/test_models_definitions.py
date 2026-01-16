from django.db import models

from core.models.LifecycleModel import ActiveManager, TimeStampedModel


class TestModel(TimeStampedModel):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'core'

class TestModelWithoutIsActive(TimeStampedModel):
    name = models.CharField(max_length=100)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'core'
