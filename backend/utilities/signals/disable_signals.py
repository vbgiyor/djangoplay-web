from contextlib import contextmanager

from django.db.models.signals import post_save, pre_save


@contextmanager
def disable_signals(*models):
    handlers = {}
    for model in models:
        handlers[model] = {
            'pre_save': [],
            'post_save': []
        }
        # Store receivers that match the model (sender)
        for receiver in pre_save.receivers:
            if len(receiver) == 3:  # Ensure receiver has the expected structure
                receiver_id, receiver_func_ref, sender = receiver
                if sender == model:
                    handlers[model]['pre_save'].append((receiver_id, receiver_func_ref))
                    pre_save.disconnect(receiver_func_ref(), sender=model)

        for receiver in post_save.receivers:
            if len(receiver) == 3:  # Ensure receiver has the expected structure
                receiver_id, receiver_func_ref, sender = receiver
                if sender == model:
                    handlers[model]['post_save'].append((receiver_id, receiver_func_ref))
                    post_save.disconnect(receiver_func_ref(), sender=model)

    try:
        yield
    finally:
        # Reconnect the stored handlers
        for model in models:
            for receiver_id, receiver_func_ref in handlers[model]['pre_save']:
                pre_save.connect(receiver_func_ref(), sender=model)
            for receiver_id, receiver_func_ref in handlers[model]['post_save']:
                post_save.connect(receiver_func_ref(), sender=model)
