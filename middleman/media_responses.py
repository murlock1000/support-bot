import logging
from typing import List

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomSendError

from middleman.chat_functions import send_media_to_room, send_reaction, send_text_to_room, find_private_msg
from middleman.handlers.EventStateHandler import EventStateHandler, RoomType, LogLevel
from middleman.handlers.MessagingHandler import MessagingHandler
from middleman.models.Chat import Chat
from middleman.models.Repositories.TicketRepository import TicketStatus
from middleman.models.Ticket import Ticket
from middleman.models.User import User
from middleman.utils import get_in_reply_to

logger = logging.getLogger(__name__)

media_name = {
    "m.image": "image",
    "m.audio": "audio",
    "m.video": "video",
    "m.file": "file",
}


class Media(object):
    def __init__(self, client, store, config, media_type, body, media_url, media_file, media_info, room, event):
        """Initialize a new Media

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            media_type (str): The type of the media

            body (str): The body of the media

            media_url (str): The url of the media

            media_file (str): The url of the encrypted media

            media_info (str): The metadata of the media

            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageMedia): The event defining the media
        """
        self.client = client
        self.store = store
        self.config = config
        self.room = room
        self.event = event
        self.media_type = media_type
        self.body = body
        self.media_url = media_url
        self.media_file = media_file
        self.media_info = media_info
        self.handler = EventStateHandler(client, store, config, room, event)
        self.messageHandler = MessagingHandler(self.handler)

    async def handle_management_room_media(self):
        reply_to = get_in_reply_to(self.event)

        if reply_to and self.config.relay_management_media:
            # Send back to original sender
            message = self.store.get_message_by_management_event_id(reply_to)
            if message:
                # Relay back to original sender
                response = await send_media_to_room(
                    self.client,
                    message["room_id"],
                    self.media_type,
                    self.body,
                    self.media_url,
                    self.media_file,
                    self.media_info,
                    reply_to_event_id=message["event_id"],
                )
                if isinstance(response, RoomSendResponse):
                    # Store our outbound reply so we can reference it later
                    self.store.store_message(
                        event_id=response.event_id,
                        management_event_id=self.event.event_id,
                        room_id=message["room_id"],
                    )
                    if self.config.confirm_reaction:
                        management_room_text = self.config.confirm_reaction_success
                    elif self.config.anonymise_senders:
                        management_room_text = f"{media_name[self.media_type]} delivered back to the sender."
                    else:
                        management_room_text = f"{media_name[self.media_type]} delivered back to the sender in " \
                                               f"room {message['room_id']}."
                    logger.info(
                        f"{media_name[self.media_type]} {self.event.event_id} relayed back to the original sender",
                    )
                else:
                    if self.config.confirm_reaction:
                        management_room_text = self.config.confirm_reaction_fail
                    else:
                        management_room_text = f"Failed to send {media_name[self.media_type]} back to sender:" \
                            f"{response.message if isinstance(response, RoomSendError) else response}"
                    logger.warning(management_room_text)
                # Confirm in management room
                if self.config.confirm_reaction:
                    await send_reaction(
                        self.client,
                        self.room.room_id,
                        self.event.event_id,
                        management_room_text
                    )
                else:
                    await send_text_to_room(
                        self.client,
                        self.room.room_id,
                        management_room_text,
                        True,
                    )
            else:
                logger.debug(
                    f"Skipping {media_name[self.media_type]} {self.event.event_id} "
                    f"which is not a reply to one of our relay messages",
                )
        else:
            logger.debug(f"Skipping {self.event.event_id} reply {media_name[self.media_type]}")



    async def process(self):
        """
        Process media.
        - if management room, identify replies and forward back to original messages.
        - anything else, relay to management room.
        """

        # Update required state based on room type
        if not await self.handler.find_room_state():
            return

        msg = "Bot received media for {} | "\
            f"{self.room.user_name(self.event.sender)} (named: {self.room.is_named}, name: {self.room.name}, "\
            f"alias: {self.room.canonical_alias}): {self.body}"

        # Combined message form
        msg = msg.format(self.handler.for_room)
        self.handler.log_console(msg, LogLevel.DEBUG)


        # Handle different scenarios
        if self.handler.room_type == RoomType.ManagementRoom:
            await self.handle_management_room_media()
        elif self.handler.room_type == RoomType.TicketRoom:
            await self.handle_ticket_room_media()
        elif self.handler.room_type == RoomType.ChatRoom:
            await self.handle_chat_room_media()
        else:
            await self.relay_from_user()

    def anonymise_text(self, anonymise: bool) -> str:
        if anonymise:
            text = None
        else:
            text = f"{self.event.sender} in {self.room.display_name} (`{self.room.room_id}`) " \
                   f"sent {media_name[self.media_type]} {self.body}:"
        return text

    async def handle_message_send(self, text, room_id):
        sender_notify_event_id = None
        if text:
            response = await send_text_to_room(self.client, room_id, text, notice=True)
            sender_notify_event_id = response.event_id
            if type(response) != RoomSendResponse or not response.event_id:
                logger.error(f"Failed to relay {media_name[self.media_type]} %s to the "
                         f"management room", self.event.event_id)
                return

        response = await send_media_to_room(
            self.client,
            room_id,
            self.media_type,
            self.body,
            self.media_url,
            self.media_file,
            self.media_info,
            reply_to_event_id=sender_notify_event_id
        )

        if type(response) == RoomSendResponse and response.event_id:
            self.store.store_message(
                self.event.event_id,
                response.event_id,
                room_id,
            )
            logger.info(f"{media_name[self.media_type]} %s relayed to the management room", self.event.event_id)
        else:
            logger.error(f"Failed to relay {media_name[self.media_type]} %s to the "
                         f"management room", self.event.event_id)

    async def handle_ticket_room_media(self):
        """Relay staff Ticket message to the client communications room."""

        if not await self.messageHandler.handle_ticket_message():
            return

        text = self.anonymise_text(True)
        await self.handle_message_send(text, self.handler.user.room_id)

    async def handle_chat_room_media(self):
        """Relay staff Chat message to the client communications room."""

        if not await self.messageHandler.handle_chat_message():
            return

        text = self.anonymise_text(True)
        await self.handle_message_send(text, self.handler.user.room_id)

    async def relay_from_user(self):
        """Relay to the management room."""

        # First check if we want to relay this
        if self.handler.is_mention_only_room([self.room.canonical_alias, self.room.room_id], self.room.is_named):
            # skip media in mention only rooms for now
            logger.debug(f"Skipping {media_name[self.media_type]} %s in room %s as it's set to "
                         f"only relay on mention and mentions are not supported for media ",
                         self.event.event_id, self.room.room_id)
            return

        # Update state for different scenarios and get room id to relay message to.
        room_id = await self.messageHandler.setup_relay()

        # Handle different relaying scenarios
        if self.handler.ticket:
            text = self.anonymise_text(True)
        elif self.handler.user.current_chat_room_id:
            text = self.anonymise_text(True)
        else:
            text = self.anonymise_text(self.config.anonymise_senders)
        await self.handle_message_send(text, room_id)

