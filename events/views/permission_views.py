from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.helpers import api_response
from events.models.event import Event
from events.models.event_permission import EventPermission
from events.serializers.event_serializer import EventPermissionSerializer


class EventPermissionView(APIView):
    permission_classes = [IsAuthenticated]

    def get_event(self, pk, user):
        event = get_object_or_404(Event, pk=pk)
        if not user.has_event_permission(event, "view"):
            raise PermissionError("You don't have permission to access this event")
        return event

    def get(self, request, event_id):
        try:
            event = self.get_event(event_id, request.user)
            permissions = EventPermission.objects.filter(event=event)
            serializer = EventPermissionSerializer(permissions, many=True)
            return api_response(
                code=status.HTTP_200_OK, message="Permissions retrieved successfully", data=serializer.data
            )
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)

    def post(self, request, event_id):
        try:
            event = self.get_event(event_id, request.user)
            if not request.user.has_event_permission(event, "edit"):
                raise PermissionError("You don't have permission to share this event")

            # Check if permission already exists
            existing_permission = EventPermission.objects.filter(
                event=event, user_id=request.data.get("user_id")
            ).first()

            if existing_permission:
                # Update existing permission
                serializer = EventPermissionSerializer(existing_permission, data=request.data, partial=True)
                if serializer.is_valid():
                    permission = serializer.save()
                    return api_response(
                        code=status.HTTP_200_OK,
                        message="Permission updated successfully",
                        data=EventPermissionSerializer(permission).data,
                    )
                return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)

            # Create new permission
            serializer = EventPermissionSerializer(data={**request.data, "event": event.id})
            if serializer.is_valid():
                permission = serializer.save(event=event, granted_by=request.user)
                return api_response(
                    code=status.HTTP_201_CREATED,
                    message="Permission granted successfully",
                    data=EventPermissionSerializer(permission).data,
                )
            return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)


class EventPermissionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_permission(self, event_id, user_id, request_user):
        event = get_object_or_404(Event, pk=event_id)
        if not request_user.has_event_permission(event, "edit"):
            raise PermissionError("You don't have permission to manage this event's permissions")
        return get_object_or_404(EventPermission, event=event, user_id=user_id)

    def put(self, request, event_id, user_id):
        try:
            permission = self.get_permission(event_id, user_id, request.user)
            serializer = EventPermissionSerializer(permission, data=request.data, partial=True)
            if serializer.is_valid():
                updated_permission = serializer.save()
                return api_response(
                    code=status.HTTP_200_OK,
                    message="Permission updated successfully",
                    data=EventPermissionSerializer(updated_permission).data,
                )
            return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)

    def delete(self, request, event_id, user_id):
        try:
            permission = self.get_permission(event_id, user_id, request.user)
            if permission.role == "owner":
                return api_response(
                    code=status.HTTP_400_BAD_REQUEST, message="Cannot remove owner permission", data=None
                )
            permission.delete()
            return api_response(code=status.HTTP_204_NO_CONTENT, message="Permission removed successfully", data=None)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)
