import logging

from django.db import transaction
from policyengine.components.permissions import get_action_based_permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from simple_history.utils import update_change_reason

logger = logging.getLogger(__name__)

class BaseBulkUpdateAPIView(APIView):
    allowed_fields = set()
    model = None
    serializer_class = None
    change_reason = "Bulk update via API"

    def get_permissions(self):
        return get_action_based_permissions(self.permission_classes)

    def patch(self, request):
        updates = request.data.get("updates", [])
        if not isinstance(updates, list):
            return Response({"error": "Invalid format: 'updates' must be a list."},
                            status=status.HTTP_400_BAD_REQUEST)

        results, errors = [], []
        for update in updates:
            object_id = update.get("id")
            if not object_id:
                errors.append({"error": "Missing ID", "data": update})
                continue

            try:
                obj = self.model.objects.get(id=object_id)
            except self.model.DoesNotExist:
                errors.append({"error": f"{self.model.__name__} with id {object_id} not found"})
                continue

            updated = False
            for field, value in update.items():
                if field == "id":
                    continue
                if field not in self.allowed_fields:
                    errors.append({"error": f"Field '{field}' not allowed", "id": object_id})
                    continue

                try:
                    setattr(obj, field, value)
                    updated = True
                except Exception as e:
                    errors.append({"error": f"Failed to update field '{field}'", "id": object_id, "reason": str(e)})

            if updated:
                try:
                    with transaction.atomic():  # Ensure atomic transaction
                        obj.save()  # Save the object to create the history record
                        # Get the latest history record for the object
                        history_record = obj.history.order_by('-history_date').first()
                        if history_record:
                            update_change_reason(obj, self.change_reason)
                        else:
                            logger.warning(f"No history record created for {self.model.__name__} id {object_id}")
                            errors.append({"error": f"No history record created for id {object_id}", "id": object_id})
                        results.append(self.serializer_class(obj).data)
                except Exception as e:
                    logger.error(f"Failed to save or update history for {self.model.__name__} id {object_id}: {str(e)}")
                    errors.append({"error": "Failed to save or update history", "id": object_id, "reason": str(e)})

        return Response({"updated": results, "errors": errors}, status=status.HTTP_200_OK)
