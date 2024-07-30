import logging
import time
from typing import Tuple, Union

# noinspection PyPackageRequirements
from nio import AsyncClient, RoomMessage, RoomGetEventResponse
from nio.rooms import MatrixRoom

from support_bot.config import Config
from support_bot.handlers.EventStateHandler import EventStateHandler, LogLevel, RoomType
from support_bot.handlers.MessagingHandler import MessagingHandler
from support_bot.models.EventPairs import EventPair
from support_bot.models.IncomingEvent import IncomingEvent
from support_bot.storage import Storage
from support_bot.utils import _get_reply_msg, get_in_reply_to, get_replaces

logger = logging.getLogger(__name__)


class Message(object):
    def __init__(self, client: AsyncClient, store: Storage, config: Config, room: MatrixRoom, event: RoomMessage):
        """Initialize a new Message

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessage): The event defining the message
        """
        self.client: AsyncClient = client
        self.store: Storage = store
        self.config: Config = config
        self.room:MatrixRoom  = room
        self.event: RoomMessage = event
        
        self.handler = EventStateHandler(client, store, config, room, event)
        self.messageHandler = MessagingHandler(self.handler)
        
        self.anonymized = self.config.anonymise_senders
        
    def construct_received_message(self, for_room:str) -> str:
        raise NotImplementedError

    async def handle_management_room_message(self):
        raise NotImplementedError

    async def process(self):
        """
        Process messages.
        - if management room, identify replies and forward back to original messages.
        - anything else, relay to management room.
        """

        # Update required state based on room type
        if not await self.handler.find_room_state():
            return

        msg = self.construct_received_message(self.handler.for_room)
        self.handler.log_console(msg, LogLevel.DEBUG)
            
        # Handle different scenarios
        if self.handler.room_type == RoomType.ManagementRoom:
            await self.handle_management_room_message()
        elif self.handler.room_type == RoomType.TicketRoom:
            await self.handle_ticket_room_message()
        elif self.handler.room_type == RoomType.ChatRoom:
            await self.handle_chat_room_message()
        else:
            # Default - message from user
            await self.relay_from_user()

    def save_incoming_event(self):
        incoming_event = IncomingEvent(self.store, self.handler.user.user_id, self.room.room_id, self.event.event_id)
        incoming_event.store_incoming_event()

    async def get_related(self, related_event_id: str) -> Union[str, None]:
        resp = await self.client.room_get_event(self.room.room_id, related_event_id)
        if isinstance(resp, RoomGetEventResponse):
            related_event_is_clone = resp.event.sender == self.client.user_id
        else:
            return None
        
        if related_event_is_clone:
            event_pair =  EventPair.get_clone_event_pair(self.store, self.room.room_id, related_event_id)
            if event_pair:
                return event_pair.event_id
        else:
            event_pair =  EventPair.get_event_pair(self.store, self.room.room_id, related_event_id)
            if event_pair:
                return event_pair.clone_event_id

    async def put_related_clone_event(self, clone_room_id: str, clone_event_id: str):
        event_pair = EventPair(self.store, self.room.room_id, self.event.event_id, clone_room_id, clone_event_id)
        event_pair.store_event_pair()
        
    async def transform_reply(self, text:str, room_id:str) -> Tuple[str, str]:
        reply_to_event_id = get_in_reply_to(self.event)
        if reply_to_event_id:
            reply_to_event_id = await self.get_related(reply_to_event_id)
            if reply_to_event_id:
                text = _get_reply_msg(self.event)
                
        return [reply_to_event_id, text]
    
    async def transform_replaces(self, text:str, room_id:str) -> Tuple[str, str]:
        replaces_event_id = get_replaces(self.event)
        if replaces_event_id:
            replaces_event_id = await self.get_related(replaces_event_id)
            if replaces_event_id:
                text = _get_reply_msg(self.event)
                
        return (replaces_event_id, text)

    async def forward_message_to_room(self, room_id:str):
        # Apply anonimization policies:
        if self.handler.ticket:
            self.anonymized = True
        elif self.handler.user.current_chat_room_id:
            self.anonymized = True
        else:
            self.anonymized = self.config.anonymise_senders
            
        # If we still don't have room data (encryption not initialized yet, or sync failed)
        # then add message to queue to be sent later
        if not self.client.rooms.get(room_id, None):
            try:
                await self.handler.message_logging_room(f"Failed to retrieve room {room_id} details to forward message from user {self.handler.user.user_id} in room {self.room.room_id}, putting message task in queue to be sent when state arrives: {self.construct_received_message(room_id)}", level=LogLevel.INFO)
            except Exception as e:
                logger.error(f"Exception thrown while sending error message: {room_id} {self.handler.user.user_id} in room {self.room.room_id}, dropping message: {self.construct_received_message(room_id)}")
            task = (self.client.callbacks._message, room_id, self.event.room_id, self.event, int(time.time()))
            # Add the task to the room queue to be sent when room is loaded
            self.client.callbacks.rooms_pending[task[1]].append(task)
            return
        
        # Otherwise, send immediately
        await self._forward_message_to_room(room_id)
        
    
    async def _forward_message_to_room(self, room_it:str):
        raise NotImplementedError()
    
    async def handle_ticket_room_message(self):
        """Relay staff Ticket message to the client communications room."""
        if not await self.messageHandler.handle_ticket_message():
            return
        
        await self.forward_message_to_room(self.handler.user.room_id)

    async def handle_chat_room_message(self):
        """Relay staff Chat message to the client communications room."""
        if not await self.messageHandler.handle_chat_message():
            return

        await self.forward_message_to_room(self.handler.user.room_id)

    def relay_based_on_mention_room(self) -> bool:
        raise NotImplementedError

    async def relay_from_user(self):
        """Relay to appropriate room (Ticket/chat/management)."""

        # First check if we want to relay this
        if not self.relay_based_on_mention_room():
            return

        # Update state for different scenarios and get room id to relay message to.
        room_id = await self.messageHandler.setup_relay()

        # Handle different relaying scenarios
        if not self.handler.ticket and not self.handler.user.current_chat_room_id:
            # Save the message event id into storage, to be copied to a ticket room later when one is raised
            self.save_incoming_event()
        await self.forward_message_to_room(room_id)
