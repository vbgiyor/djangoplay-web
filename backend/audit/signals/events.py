from django.dispatch import Signal

# Fired AFTER a model is soft-deleted
post_soft_delete = Signal()

# Fired AFTER a model is restored
post_restore = Signal()
