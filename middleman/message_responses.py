import logging
import re

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomSendError, AsyncClient
from nio.rooms import MatrixRoom
from nio.events.room_events import RoomMessageText

from middleman.bot_commands import Command
from middleman.chat_functions import send_reaction, send_text_to_room
from middleman.config import Config
from middleman.handlers.EventStateHandler import EventStateHandler, LogLevel, RoomType
from middleman.handlers.MessagingHandler import MessagingHandler
from middleman.models.IncomingEvent import IncomingEvent
from middleman.storage import Storage
from middleman.utils import get_in_reply_to, get_mentions, get_replaces, get_reply_msg, get_raise_msg

logger = logging.getLogger(__name__)


class Message(object):
    def __init__(self, client, store, config, message_content, room, event):
        """Initialize a new Message

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            message_content (str): The body of the message

            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message
        """
        self.client: AsyncClient = client
        self.store: Storage = store
        self.config: Config = config
        self.message_content: str = message_content
        self.room:MatrixRoom  = room
        self.event: RoomMessageText = event
        self.handler = EventStateHandler(client, store, config, room, event)
        self.messageHandler = MessagingHandler(self.handler)

    async def handle_management_room_message(self):
        reply_to = get_in_reply_to(self.event)
        replaces = get_replaces(self.event)


        reply_section = get_reply_msg(self.event, reply_to, replaces)
        raise_section = get_raise_msg(self.event, reply_to, replaces)

        if not reply_section:
            if not raise_section:
                logger.debug(
                    f"Skipping {self.event.event_id} which does not look like a reply"
                )
                return
            #raise_text = raise_section[raise_section.find("!raise ") + 7:]
            #logger.debug(f"RAISE: {raise_text}")
            if reply_to:
                message = self.store.get_message_by_management_event_id(reply_to)
                if message:
                    reply_rx_pattern = re.compile(r".+(@[^\s]*)")
                    match = reply_rx_pattern.match(self.event.body)

                    if match:
                        rx_id = match[1]  # Get the id from regex group
                        command = Command(self.client, self.store, self.config, raise_section[1:7]+rx_id+raise_section[6:], self.room, self.event)
                        await command.process()

        elif reply_to:
            # Send back to original sender
            message = self.store.get_message_by_management_event_id(reply_to)
            if not message:
                logger.debug(
                    f"Skipping message {self.event.event_id} which is not a reply to one of our relay messages",
                )
                return
            # Relay back to original sender
            # Send back anything after !reply
            reply_text = reply_section[reply_section.find("!reply ") + 7:]
            response = await send_text_to_room(
                self.client,
                message["room_id"],
                reply_text,
                False,
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
                    management_room_text = "Message delivered back to the sender."
                else:
                    management_room_text = f"Message delivered back to the sender in room {message['room_id']}."
                logger.info(f"Message {self.event.event_id} relayed back to the original sender")
            elif isinstance(response, RoomSendError):
                if self.config.confirm_reaction:
                    management_room_text = self.config.confirm_reaction_fail
                else:
                    management_room_text = f"Failed to send message back to sender: {response.message}"
                logger.warning(management_room_text)
            else:
                if self.config.confirm_reaction:
                    management_room_text = self.config.confirm_reaction_fail
                else:
                    management_room_text = f"Failed to send message back to sender: {response}"
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
        elif replaces:
            # Edit the already sent reply event
            message = self.store.get_message_by_management_event_id(replaces)
            if not message:
                logger.debug(
                    f"Skipping message {self.event.event_id} which is not an edit to one of our reply messages",
                )
                return
            # Edit the previously sent event
            # Send back anything after !reply
            reply_text = reply_section[reply_section.find("!reply ") + 7:]
            response = await send_text_to_room(
                self.client,
                message["room_id"],
                reply_text,
                False,
                replaces_event_id=message["event_id"],
            )
            if isinstance(response, RoomSendResponse):
                # Store our outbound reply so we can reference it later
                self.store.store_message(
                    event_id=response.event_id,
                    management_event_id=self.event.event_id,
                    room_id=message["room_id"],
                )
                if self.config.anonymise_senders:
                    management_room_text = "Edit delivered back to the sender."
                else:
                    management_room_text = f"Edit delivered back to the sender in " \
                                            f"room {message['room_id']}."
                logger.info(f"Edit {self.event.event_id} relayed back to the original sender")
            elif isinstance(response, RoomSendError):
                management_room_text = f"Failed to send edit back to sender: {response.message}"
                logger.warning(management_room_text)
            else:
                management_room_text = f"Failed to send edit back to sender: {response}"
                logger.warning(management_room_text)
            # Confirm in management room
            await send_text_to_room(
                self.client,
                self.room.room_id,
                management_room_text,
                True,
            )

    async def process(self):
        """
        Process messages.
        - if management room, identify replies and forward back to original messages.
        - anything else, relay to management room.
        """

        # Update required state based on room type
        if not await self.handler.find_room_state():
            return

        msg = "Bot message received for {} | "\
            f"{self.room.user_name(self.event.sender)} (named: {self.room.is_named}, name: {self.room.name}, "\
            f"alias: {self.room.canonical_alias}): {self.message_content}"

        # Combined message form
        msg = msg.format(self.handler.for_room)
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

    def anonymise_text(self, anonymise: bool) -> str:
        if anonymise:
            text = f"{self.message_content}".replace("\n", "  \n")
        else:
            text = f"{self.event.sender} in {self.room.display_name} (`{self.room.room_id}`): " \
                   f"{self.message_content}".replace("\n", "  \n")
        return text

    async def send_message_to_room(self, text, room):
        response = await send_text_to_room(self.client, room, text, False)
        if type(response) == RoomSendResponse and response.event_id:
            try:
                self.store.store_message(
                    self.event.event_id,
                    response.event_id,
                    self.room.room_id,
                )
            except:
                # When cloning messages after creating a new ticket room - messages will be sent again with identical event ids.
                pass
            logger.info("Message %s relayed to room %s", self.event.event_id, self.room.room_id)
        else:
            logger.error("Failed to relay message %s to room %s", self.event.event_id, self.room.room_id)
            
    async def handle_ticket_room_message(self):
        """Relay staff Ticket message to the client communications room."""
        if not await self.messageHandler.handle_ticket_message():
            return

        text = self.anonymise_text(True)
        await self.send_message_to_room(text, self.handler.user.room_id)

    async def handle_chat_room_message(self):
        """Relay staff Chat message to the client communications room."""
        if not await self.messageHandler.handle_chat_message():
            return

        text = self.anonymise_text(True)
        await self.send_message_to_room(text, self.handler.user.room_id)

    async def relay_from_user(self):
        """Relay to appropriate room (Ticket/chat/management)."""

        # First check if we want to relay this
        if self.handler.is_mention_only_room([self.room.canonical_alias, self.room.room_id], self.room.is_named):
            # Did we get mentioned?
            mentioned = self.config.user_id in get_mentions(self.message_content) or \
                        self.message_content.lower().find(self.config.user_localpart.lower()) > -1
            if not mentioned:
                logger.debug("Skipping message %s in room %s as it's set to only relay on mention and we were not "
                             "mentioned.", self.event.event_id, self.room.room_id)
                return
            logger.info("Room %s marked as mentions only and we have been mentioned, so relaying %s",
                        self.room.room_id, self.event.event_id)

        # Update state for different scenarios and get room id to relay message to.
        room_id = await self.messageHandler.setup_relay()

        # Handle different relaying scenarios
        if self.handler.ticket:
            text = self.anonymise_text(True)
        elif self.handler.user.current_chat_room_id:
            text = self.anonymise_text(True)
        else:
            # Save the message event id into storage, to be sent to a ticket room later
            self.save_incoming_event()
            text = self.anonymise_text(self.config.anonymise_senders)
        await self.send_message_to_room(text, room_id)
