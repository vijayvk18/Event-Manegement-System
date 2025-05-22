from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import api_response
from events.models.event import Event
from events.models.event_permission import EventPermission
from events.serializers.permission_serializer import EventPermissionSerializer
from events.utils.changelog_utils import create_changelog_entry, get_permission_data


class EventPermissionView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_event(self, event_id, user):
        # Get the event
        event = get_object_or_404(Event, id=event_id)

        # Get the root event
        root_event = event.parent_version or event

        # Check permissions on root event
        if not user.has_event_permission(root_event, "view"):
            raise PermissionError("You don't have permission to view this event")
        return root_event

    def get(self, request, event_id):
        try:
            event = self.get_event(event_id, request.user)
            permissions = EventPermission.objects.filter(event=event)
            serializer = EventPermissionSerializer(permissions, many=True, context={"event": event})
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

            # Store previous permissions for changelog
            previous_permissions = list(EventPermission.objects.filter(event=event).values())

            serializer = EventPermissionSerializer(data=request.data, context={"event": event})
            if serializer.is_valid():
                permission = serializer.save(event=event, granted_by=request.user)

                # Create changelog entry for permission addition
                create_changelog_entry(
                    event=event,
                    user=request.user,
                    change_type="permission_add",
                    previous_data=previous_permissions,
                    new_data=get_permission_data(permission),
                    old_version=None,
                    new_version=None,
                )

                return api_response(
                    code=status.HTTP_201_CREATED,
                    message="Permission added successfully",
                    data=EventPermissionSerializer(permission, context={"event": event}).data,
                )
            return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)


class EventPermissionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_event(self, event_id, user):
        # Get the event
        event = get_object_or_404(Event, id=event_id)

        # Get the root event
        root_event = event.parent_version or event

        # Check permissions on root event
        if not user.has_event_permission(root_event, "view"):
            raise PermissionError("You don't have permission to view this event")
        return root_event

    def get_permission(self, event_id, permission_id, user):
        event = self.get_event(event_id, user)
        permission = get_object_or_404(EventPermission, id=permission_id, event=event)
        return permission

    def put(self, request, event_id, permission_id):
        try:
            permission = self.get_permission(event_id, permission_id, request.user)
            if not request.user.has_event_permission(permission.event, "edit"):
                raise PermissionError("You don't have permission to modify permissions")

            # Store previous permission data for changelog
            previous_data = get_permission_data(permission)

            serializer = EventPermissionSerializer(
                permission, data=request.data, partial=True, context={"event": permission.event}
            )
            if serializer.is_valid():
                updated_permission = serializer.save()

                # Create changelog entry for permission update
                create_changelog_entry(
                    event=permission.event,
                    user=request.user,
                    change_type="permission_update",
                    previous_data=previous_data,
                    new_data=get_permission_data(updated_permission),
                    old_version=None,
                    new_version=None,
                )

                return api_response(
                    code=status.HTTP_200_OK,
                    message="Permission updated successfully",
                    data=EventPermissionSerializer(updated_permission, context={"event": permission.event}).data,
                )
            return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)

    def delete(self, request, event_id, permission_id):
        try:
            permission = self.get_permission(event_id, permission_id, request.user)
            if not request.user.has_event_permission(permission.event, "edit"):
                raise PermissionError("You don't have permission to delete permissions")

            # Store permission data for changelog before deletion
            permission_data = get_permission_data(permission)

            # Create changelog entry before deletion
            create_changelog_entry(
                event=permission.event,
                user=request.user,
                change_type="permission_delete",
                previous_data=permission_data,
                new_data=None,
                old_version=None,
                new_version=None,
            )

            permission.delete()
            return api_response(code=status.HTTP_204_NO_CONTENT, message="Permission deleted successfully", data=None)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)
