import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from core.models.user import User
from events.models.event import Event
from events.models.event_permission import EventPermission


class EventConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Called when a WebSocket connection is established
        """
        # Authenticate the connection
        authenticated = await self.authenticate()
        if not authenticated:
            await self.close()
            return

        # Add the client to the events group and their personal group
        await self.channel_layer.group_add("events", self.channel_name)
        await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)

        # Subscribe to user's event groups
        event_ids = await self.get_user_events()
        for event_id in event_ids:
            await self.channel_layer.group_add(f"event_{event_id}", self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        """
        Called when a WebSocket connection is closed
        """
        if hasattr(self, "user"):
            # Remove from user's personal group
            await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)

            # Remove from event groups
            event_ids = await self.get_user_events()
            for event_id in event_ids:
                await self.channel_layer.group_discard(f"event_{event_id}", self.channel_name)

        # Remove from general events group
        await self.channel_layer.group_discard("events", self.channel_name)

    async def receive(self, text_data):
        """
        Called when a message is received from the WebSocket
        """
        try:
            data = json.loads(text_data)
            action = data.get("action")
            event_id = data.get("event_id")

            if action == "get_event":
                event = await self.get_event(event_id)
                if event:
                    await self.send(text_data=json.dumps({"type": "event_details", "event": event}))
                else:
                    await self.send(text_data=json.dumps({"type": "error", "message": "Event not found"}))
            elif action == "subscribe" and event_id:
                # Check if user has permission to subscribe
                if await self.has_event_permission(event_id):
                    await self.channel_layer.group_add(f"event_{event_id}", self.channel_name)
                    await self.send(
                        text_data=json.dumps({"type": "subscription", "status": "subscribed", "event_id": event_id})
                    )
            elif action == "unsubscribe" and event_id:
                await self.channel_layer.group_discard(f"event_{event_id}", self.channel_name)
                await self.send(
                    text_data=json.dumps({"type": "subscription", "status": "unsubscribed", "event_id": event_id})
                )

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON format"}))
        except Exception as e:
            await self.send(text_data=json.dumps({"type": "error", "message": str(e)}))

    async def event_update(self, event):
        """
        Called when an event is updated, broadcasts to all connected clients in the event group
        """
        await self.channel_layer.group_send(f"event_{event['id']}", {"type": "broadcast_event_update", "event": event})

    async def broadcast_event_update(self, event):
        """
        Broadcasts event updates to all connected clients
        """
        await self.send(text_data=json.dumps({"type": "event_update", "event": event}))

    @database_sync_to_async
    def get_event(self, event_id):
        """
        Get event details from database
        """
        try:
            event = Event.objects.get(id=event_id)
            return {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "start_date": event.start_date.isoformat(),
                "end_date": event.end_date.isoformat(),
                "location": event.location,
                "status": event.status,
            }
        except ObjectDoesNotExist:
            return None

    @database_sync_to_async
    def get_user_events(self):
        """Get all event IDs the user has access to"""
        event_permissions = EventPermission.objects.filter(user=self.user).values_list("event_id", flat=True)
        return [str(event_id) for event_id in event_permissions]

    @database_sync_to_async
    def has_event_permission(self, event_id):
        """Check if user has permission to access the event"""
        return EventPermission.objects.filter(user=self.user, event_id=event_id).exists()

    async def authenticate(self):
        """Authenticate the WebSocket connection using JWT"""
        try:
            # Get the token from the query string
            token_key = self.scope.get("query_string", b"").decode().split("token=")[-1]
            if not token_key:
                return False

            # Validate token
            access_token = AccessToken(token_key)
            user_id = access_token["user_id"]
            self.user = await self.get_user(user_id)
            return self.user is not None and self.user.is_authenticated
        except (InvalidToken, TokenError, ValueError, IndexError):
            return False

    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
