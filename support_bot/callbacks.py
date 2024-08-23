from collections import defaultdict
import json
import logging
from datetime import datetime
import time

# noinspection PyPackageRequirements
from nio import (
    JoinError, MatrixRoom, Event, RoomKeyEvent, RoomMessageText, MegolmEvent, LocalProtocolError,
    RoomKeyRequestError, RoomMemberEvent, Response, RoomKeyRequest, RedactionEvent, CallInviteEvent,
    AsyncClient, CallEvent, RoomEncryptionEvent, ErrorResponse
)

from support_bot.bot_commands import Command
from support_bot.call_event_message_responses import CallEventMessage
from support_bot.chat_functions import send_text_to_room, send_shared_history_keys
from support_bot.config import Config
from support_bot.media_responses import Media
from support_bot.message_responses import TextMessage
from support_bot.models.Repositories.TicketRepository import TicketStatus
from support_bot.models.Staff import Staff
from support_bot.redact_responses import RedactMessage
from support_bot.storage import Storage
from support_bot.models.Support import Support
from support_bot.utils import with_ratelimit

from support_bot.models.Ticket import Ticket, ticket_name_pattern
from support_bot.models.User import User

logger = logging.getLogger(__name__)

DUPLICATES_CACHE_SIZE = 1000


class Callbacks(object):
    def __init__(self, client: AsyncClient, store: Storage, config: Config):
        """
        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters
        """
        self.client: AsyncClient = client
        self.store = store
        self.config = config
        self.command_prefix = config.command_prefix
        self.received_events = []
        self.welcome_message_sent_to_room = []
        self.rooms_pending = defaultdict(list)

    async def decrypted_callback(self, room_id: str, event: RoomMessageText):
        if isinstance(event, RoomMessageText):
            await self.message(self.client.rooms[room_id], event)
        else:
            logger.warning(f"Unknown event %s passed to decrypted_callback" % event)

    async def decryption_failure(self, room: MatrixRoom, event: MegolmEvent):
        """Callback for when an event fails to decrypt."""
        # If ignoring old messages, ignore messages older than 5 minutes
        if self.config.ignore_old_messages:
            if (
                    datetime.now() - datetime.fromtimestamp(event.server_timestamp / 1000.0)
            ).total_seconds() > 300:
                return
        message = f"Failed to decrypt event {event.event_id} in room {room.name} ({room.canonical_alias} / " \
                  f"{room.room_id}) from {event.sender} (session {event.session_id} - decrypting " \
                  f"if keys arrive."
        logger.warning(message)

        # Store for later
        self.store.store_encrypted_event(event)

        waiting_for_keys = self.store.get_encrypted_events_for_user(event.sender)
        logger.info(
            "Waiting to decrypt %s events from sender %s",
            len(waiting_for_keys), event.sender,
        )

        # Send a request for the key
        response = None
        try:
            response = await self.client.request_room_key(event)
        except LocalProtocolError as ex:
            if str(ex) != "A key sharing request is already sent out for this session id.":
                logger.warning(f"Failed to request room key for event {event.event_id}: {ex}")
        if isinstance(response, RoomKeyRequestError):
            logger.warning("RoomKeyRequestError: %s (%s)", response.message, response.status_code)

        # Send a message to the management room if
        # * matrix logging is not enabled
        # * room is not named (ie dm normally)
        if not self.config.matrix_logging_room or not room.is_named:
            await send_text_to_room(
                client=self.client,
                room=self.config.management_room_id,
                message=f"{message} Warning! The room is a direct message.",
                notice=True,
            )

    def trim_duplicates_caches(self):
        if len(self.received_events) > DUPLICATES_CACHE_SIZE:
            self.received_events = self.received_events[:DUPLICATES_CACHE_SIZE]
        if len(self.welcome_message_sent_to_room) > DUPLICATES_CACHE_SIZE:
            self.welcome_message_sent_to_room = self.welcome_message_sent_to_room[:DUPLICATES_CACHE_SIZE]

    async def member(self, room: MatrixRoom, event: RoomMemberEvent) -> None:
        """Callback for when a room member event is received.

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMemberEvent): The event
        """
        # If ignoring old messages, ignore messages older than 5 minutes
        if self.config.matrix_logging_room and room.room_id == self.config.matrix_logging_room:
            # Don't react to anything in the logging room
            return

        self.trim_duplicates_caches()
        if self.should_process(event.event_id) is False:
            return
        logger.debug(
            f"Received a room member event for {room.display_name} | "
            f"{event.sender}: {event.membership} {event}"
        )

        # Ignore our support bot membership events
        if event.state_key == self.client.user:
            return
        
        # If user left their primary communications room
        if event.membership == 'leave':
            user = User.get_existing(self.store, event.sender)
            if user:
                if user.room_id == room.room_id:
                    logger.info(f"User {user.user_id} left the primary communications channel room {room.room_id}. /"
                                f"Unable to send messages to user until communications room is recreated.")
                    user.update_communications_room(None)
        elif event.membership == 'join':
            support = Support.get_existing(self.store, event.sender)
            if not support:
                support = Staff.get_existing(self.store, event.sender)
            if not support:
                return
            
            try:
                resp = await send_shared_history_keys(self.client, room.room_id, [support.user_id])
                if isinstance(resp, ErrorResponse):
                    logger.warning(f"Failed to share history keys for user {support.user_id} in room {room.room_id} : {resp.message}")
            except Exception as e:
                logger.error(e)

        elif event.membership == 'invite':
            # Ignore invites sent by us
            if event.sender == self.client.user:
                return
            # Get the user who invited the bot
            room_creator = User.get_existing(self.store, room.creator)
            if not room_creator:
                # Create new User entry if doesn't exist yet
                room_creator = User.create_new(self.store, room.creator)

            logger.debug(f"Support bot invited by: {room_creator.user_id}")

            # Update User Communication room id
            room_creator.update_communications_room(room.room_id)
            logger.debug(f"Set new communications room for user to: {room_creator.user_id}")

            # Send welcome message if configured
            if self.config.welcome_message: # and room.is_group:
                #if room.room_id in self.welcome_message_sent_to_room:
                #    logger.debug(f"Not sending welcome message to room {room.room_id} - it's been sent already!")
                #    return
                # Send welcome message
                logger.info(f"Sending welcome message to room {room.room_id}")
                self.welcome_message_sent_to_room.insert(0, room.room_id)
                await send_text_to_room(self.client, room.room_id, self.config.welcome_message, True)

            # Notify the management room for visibility
            logger.info(f"Notifying management room of room join to {room.room_id}")
            await send_text_to_room(
                self.client,
                self.config.management_room_id,
                f"I have joined room {room.display_name} (`{room.room_id}`).",
                True,
            )

    async def check_awaited(self, response) -> None:
        to_delete = []
        for room_id in self.rooms_pending.keys():
            if self.client.rooms.get(room_id, None) and room_id in self.client.encrypted_rooms:
                for message_task in self.rooms_pending[room_id]:
                    try:
                        msg = f"Executing queued task for room {room_id}"
                        logger.info(msg)
                        await message_task[0](self.client.rooms[message_task[2]], message_task[3])
                    except Exception as e:
                        logger.error(f"Error performing queued task after joining room: {e}")
                to_delete.append(room_id)
            else:
                ts = int(time.time())
                live_tasks = []
                for message_task in self.rooms_pending[room_id]:
                    # Check if room hasn't been fetched in the past 300 seconds
                    if (ts-message_task[4]) >= 300:
                        msg = (f"Task destined to room {message_task[2]} DROPPED due to not receiving encryption/room state for > 300s. DROPPING message from {message_task[3].sender} - {message_task[3].body}")
                        try:
                            logger.error(msg)
                            await send_text_to_room(self.client, self.config.matrix_logging_room, msg)
                        except Exception as e:
                            logger.error(f"Exception thrown while sending error message: {room_id}")
                    else:
                        live_tasks.append(message_task)
                        
                if live_tasks == []:
                    to_delete.append(room_id)
                else:
                    self.rooms_pending[room_id] = live_tasks
        
        for room_id in to_delete:
            del self.rooms_pending[room_id]


    async def room_encryption(self, room: MatrixRoom, event: RoomEncryptionEvent) -> None:
        """Callback for when an event signaling that encryption has been enabled in a room is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomEncryptionEvent): The event
        """
        ## Send all pending messages for the room when invited at least one user to the room (so encryption is initialized)
        logger.info(f"Room encryption enabled in room {room.room_id}")
        
        await self.check_awaited(None)
    
    async def call_event(self, room: MatrixRoom, event: CallEvent):
        """Callback for when a m.call.invite event is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.CallInviteEvent): The event defining the message

        """

        # If ignoring old messages, ignore messages older than 5 minutes
        if self.config.ignore_old_messages:
            if (
                    datetime.now() - datetime.fromtimestamp(event.server_timestamp / 1000.0)
            ).total_seconds() > 300:
                return
        if self.config.matrix_logging_room and room.room_id == self.config.matrix_logging_room:
            # Don't react to anything in the logging room
            return

        self.trim_duplicates_caches()
        if self.should_process(event.event_id) is False:
            return
        
        await self._call_event(room, event)

    async def redact(self, room, event):
        """Callback for when a redact event is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message

        """
        # If ignoring old messages, ignore messages older than 5 minutes
        if self.config.ignore_old_messages:
            if (
                    datetime.now() - datetime.fromtimestamp(event.server_timestamp / 1000.0)
            ).total_seconds() > 300:
                return
        if self.config.matrix_logging_room and room.room_id == self.config.matrix_logging_room:
            # Don't react to anything in the logging room
            return

        self.trim_duplicates_caches()
        if self.should_process(event.event_id) is False:
            return
        
        await self._redact(room, event)
        
    async def _call_event(self, room: MatrixRoom, event: CallEvent):
        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        event_type = event.source["type"]

        call_invite = CallEventMessage(self.client, self.store, self.config, room, event, event_type)
        await call_invite.process()
    
    async def _redact(self, room, event: RedactionEvent):
        # Extract the redact information
        redacts_event_id = event.redacts
        reason = event.reason

        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        redact = RedactMessage(self.client, self.store, self.config, room, event, redacts_event_id, reason)
        await redact.process()
        

    async def message(self, room:MatrixRoom, event):
        """Callback for when a message event is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message

        """
        await self.client.room_get_state(room.room_id)
        # If ignoring old messages, ignore messages older than 5 minutes
        if self.config.ignore_old_messages:
            if (
                    datetime.now() - datetime.fromtimestamp(event.server_timestamp / 1000.0)
            ).total_seconds() > 300:
                return
        if self.config.matrix_logging_room and room.room_id == self.config.matrix_logging_room:
            # Don't react to anything in the logging room
            return

        self.trim_duplicates_caches()
        if self.should_process(event.event_id) is False:
            return
        
        await self._message(room, event)

    async def _message(self, room, event):
        # Extract the message text
        msg = event.body

        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        # If this looks like an edit, strip the edit prefix
        if msg.startswith(" * "):
            msg = msg[3:]

        # Process as message if in a public room without command prefix
        # TODO Implement check of named commands using an array
        has_command_prefix = msg.startswith(self.command_prefix) or msg.startswith("!message")

        if has_command_prefix:
            if msg.startswith("!message"):
                msg = msg[1:]
            else:
                # Remove the command prefix
                msg = msg[len(self.command_prefix):]

            command = Command(self.client, self.store, self.config, msg, room, event)
            await command.process()
        else:
            # General message listener
            message = TextMessage(self.client, self.store, self.config, room, event, msg)
            await message.process()

    async def media(self, room, event):
        """Callback for when a media event is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageMedia): The event defining the media

        """
        # If ignoring old messages, ignore messages older than 5 minutes
        if self.config.ignore_old_messages:
            if (
                    datetime.now() - datetime.fromtimestamp(event.server_timestamp / 1000.0)
            ).total_seconds() > 300:
                return
        if self.config.matrix_logging_room and room.room_id == self.config.matrix_logging_room:
            # Don't react to anything in the logging room
            return

        self.trim_duplicates_caches()
        if self.should_process(event.event_id) is False:
            return

        # Ignore medias from ourselves
        if event.sender == self.client.user:
            return
        
        await self._media(room, event)

    async def _media(self, room, event):
        # Extract media type
        msgtype = event.source.get("content").get("msgtype")

        # Extract media body
        body = event.body

        # Extract media url
        media_url = event.source.get("content").get("url")

        # Extract media file
        media_file = event.source.get("content").get("file")

        # Extract media info
        media_info = event.source.get("content").get("info")

        # General media listener
        media = Media(
            self.client, self.store, self.config, room, event, msgtype, body, media_url, media_file, media_info
        )
        await media.process()

    async def invite(self, room, event):
        """Callback for when an invitation is received. Join the room specified in the invite"""
        if self.should_process(event.source.get("event_id")) is False:
            return
        logger.debug(f"Got invite to {room.room_id} from {event.sender}.")

        result = await with_ratelimit(self.client.join)(room.room_id)
        if type(result) == JoinError:
            logger.error("Unable to join room: %s", room.room_id)
            return

        logger.info(f"Joined {room.room_id}")

    async def room_key(self, event: RoomKeyEvent):
        """Callback for ToDevice events like room key events."""
        events = self.store.get_encrypted_events(event.session_id)
        waiting_for_keys = self.store.get_encrypted_events_for_user(event.sender)
        if len(events):
            log_func = logger.info
        else:
            log_func = logger.debug
        log_func(
            "Got room key event for session %s, user %s, matched sessions: %s",
            event.session_id, event.sender, len(events),
        )
        log_func(
            "Waiting to decrypt %s events from sender %s",
            len(waiting_for_keys), event.sender,
        )

        if not events:
            return

        for encrypted_event in events:
            try:
                event_dict = json.loads(encrypted_event["event"])
                params = event_dict["source"]
                params["room_id"] = event_dict["room_id"]
                params["transaction_id"] = event_dict["transaction_id"]
                megolm_event = MegolmEvent.from_dict(params)
            except Exception as ex:
                logger.warning("Failed to restore MegolmEvent for %s: %s", encrypted_event["event_id"], ex)
                continue
            try:
                # noinspection PyTypeChecker
                decrypted = self.client.decrypt_event(megolm_event)
            except Exception as ex:
                logger.warning("Error decrypting event %s: %s", megolm_event.event_id, ex)
                continue
            if isinstance(decrypted, Event):
                logger.info("Successfully decrypted stored event %s", decrypted.event_id)
                parsed_event = Event.parse_event(decrypted.source)
                logger.info("Parsed event: %s", parsed_event)
                self.store.remove_encrypted_event(decrypted.event_id)
                # noinspection PyTypeChecker
                await self.decrypted_callback(encrypted_event["room_id"], parsed_event)
            else:
                logger.warning("Failed to decrypt event %s", decrypted.event_id)

    async def room_key_request(self, event: RoomKeyRequest):
        """Callback for ToDevice RoomKeyRequest events from unverified device."""

        user_id = event.sender
        device_id = event.requesting_device_id
        device = self.client.device_store[user_id][device_id]

        self.client.verify_device(device)
        for request in self.client.get_active_key_requests(
                user_id, device_id):
            res = self.client.continue_key_share(request)

    def should_process(self, event_id: str) -> bool:
        logger.debug("Callback received event: %s", event_id)
        if event_id in self.received_events:
            logger.debug("Skipping %s as it's already processed", event_id)
            return False
        self.received_events.insert(0, event_id)
        return True
