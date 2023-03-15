import logging

# noinspection PyPackageRequirements
from nio import AsyncClient, RoomRedactResponse
from nio.rooms import MatrixRoom
from nio.events.room_events import CallInviteEvent

from middleman.event_responses import Message
from middleman.chat_functions import send_text_to_room
from middleman.config import Config
from middleman.handlers.EventStateHandler import RoomType
from middleman.storage import Storage

logger = logging.getLogger(__name__)


class CallInvite(Message):
    def __init__(self, client: AsyncClient, store: Storage, config: Config, room: MatrixRoom, event: CallInviteEvent):
        """Initialize a new call invite Message

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.CallInviteEvent): The event defining the message
            
        """
        super().__init__(client, store, config, room, event)

    async def handle_management_room_message(self):
        return
    
    def construct_received_message(self) -> str:
        return "Bot call invite event received for {} | "\
            f"{self.room.user_name(self.event.sender)} (named: {self.room.is_named}, name: {self.room.name}, "\
            f"alias: {self.room.canonical_alias}): "

    def anonymise_text(self, anonymise: bool) -> str:
        return ""
        
    async def send_notice_to_room(self, room_id:str):
        if not self.client.rooms.get(room_id, None):
            task = (self.client.callbacks._redact, room_id, self.event.room_id, self.event)
            if task[1] not in self.client.callbacks.rooms_pending:
                self.client.callbacks.rooms_pending[task[1]] = []

            self.client.callbacks.rooms_pending[task[1]].append(task)
            return
        
        text = f"Call event received from user: {self.event.sender} in room {self.room.room_id}"
        response = await send_text_to_room(self.client, room_id, text, False)
        
        if type(response) == RoomRedactResponse and response.event_id:
            logger.info("Call invite even %s relayed to room %s", self.event.event_id, self.room.room_id)
        else:
            logger.error("Failed to relay call invite event %s to room %s", self.event.event_id, self.room.room_id)
    
    async def send_message_to_room(self, text:str, room_id:str):

        # Only relay user messages.
        if self.handler.room_type != RoomType.UserRoom:
            return 

        await self.send_notice_to_room(room_id)

    def relay_based_on_mention_room(self) -> bool:
        return True