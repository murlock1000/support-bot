from __future__ import annotations
import json
import logging
import time
from typing import Optional

# noinspection PyPackageRequirements
from nio import (RoomSendResponse, 
                 RoomCreateResponse, 
                 RoomInviteResponse,
                 RoomCreateError,
                 RoomGetEventResponse,
                 AsyncClient,
                 RoomMessageNotice,
                 RoomMessageFormatted,
                 RoomMessageMedia,
                 RoomEncryptedMedia,
                 ErrorResponse,
                 RoomKickError,
                 SyncResponse,
                 SyncError,
                 RoomLeaveError,
                 RoomForgetError,
                )
from nio.rooms import MatrixRoom
from nio.events.room_events import RoomMessageText

from support_bot import commands_help
from support_bot.chat_functions import create_private_room, filtered_sync, get_room_messages, invite_to_room, send_text_to_room, kick_from_room, \
    find_private_msg, send_shared_history_keys, delete_room
from support_bot.config import Config
from support_bot.errors import Errors, TicketNotFound, ChatNotFound
from support_bot.handlers.EventStateHandler import EventStateHandler, LogLevel, RoomType
from support_bot.handlers.MessagingHandler import MessagingHandler
from support_bot.models.Chat import Chat
from support_bot.models.EventPairs import EventPair
from support_bot.models.IncomingEvent import IncomingEvent
from support_bot.models.Repositories.ChatRepository import ChatStatus, ChatRepository
from support_bot.models.Repositories.TicketRepository import TicketStatus, TicketRepository
from support_bot.models.Staff import Staff
from support_bot.models.Support import Support
from support_bot.models.Ticket import Ticket
from support_bot.models.User import User
from support_bot.storage import Storage
from support_bot.utils import get_replaces, get_username

logger = logging.getLogger(__name__)

class Command(object):
    def __init__(self, client: AsyncClient, store: Storage, config: Config, command: str, room: MatrixRoom, event: RoomMessageText):
        """A command made by a user

        Args:
            client (nio.AsyncClient): The client to communicate to matrix with

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            command (str): The command and arguments

            room (nio.rooms.MatrixRoom): The room the command was sent in

            event (nio.events.room_events.RoomMessageText): The event describing the command
        """
        self.client: AsyncClient = client
        self.store: Storage = store
        self.config: Config = config
        self.command: str = command
        self.room: MatrixRoom = room
        self.event: RoomMessageText = event
        self.args = self.command.split()[1:]
        self.handler = EventStateHandler(client, store, config, room, event)
        self.messageHandler = MessagingHandler(self.handler)

    async def process(self):

        # Update required state based on room type
        if not await self.handler.find_room_state():
            return

        if not self.handler.find_state_staff():
            msg = f"{self.event.sender} in room {self.room.room_id} | {self.room.name} \
            is unauthorized to use {self.command}"
            await self.handler.message_management(msg, LogLevel.INFO)
            return

        """Process the command"""
        if self.command.startswith("echo"):
            await self._echo()
        elif self.command.startswith("help"):
            await self._show_help()
        #elif self.command.startswith("message"):
        #    await self._message()
        elif self.command.startswith("claimfor"):
            await self._claimfor()
        elif self.command.startswith("claim"):
            await self._claim()
        elif self.command.startswith("raise"):
            await self._raise_ticket()
        elif self.command.startswith("close"):
            await self._close_room()
        elif self.command.startswith("forcecloseticket"):
            await self._force_close_ticket()
        elif self.command.startswith("forceclosechat"):
            await self._force_close_chat()
        elif self.command.startswith("reopen"):
            await self._reopen_ticket()
        elif self.command.startswith("opentickets"):
            await self._open_tickets()
        elif self.command.startswith("openchats"):
            await self._open_chats()
        elif self.command.startswith("activeticket"):
            await self._show_active_user_ticket()
        elif self.command.startswith("activechat"):
            await self._show_active_user_chat()
        elif self.command.startswith("addstaff"):
            await self._add_staff()
        elif self.command.startswith("setupcommunicationsroom"):
            await self._setup_communications_room()
        elif self.command.startswith("printroomstate"):
            await self._print_room_state()
        elif self.command.startswith("fetchroomstate"):
            await self._fetch_room_state()
        elif self.command.startswith("_deleteroomstate"):
            await self.__delete_room_state()
        elif self.command.startswith("_deleteticketroom"):
            await self.__delete_ticket_room()
        elif self.command.startswith("_deletechatroom"):
            await self.__delete_chat_room()
        elif self.command.startswith("messageroom"):
            await self._message_room()
        elif self.command.startswith("chat"):
            await self._chat()
        else:
            await self._unknown_command()

    # ## Decorators
    # def with_staff(f):
    #     async def wrapper(self, *args, **kwargs):
    #         self.handler.staff = Staff.get_existing(self.store, self.event.sender)
    #         if self.handler.staff:
    #             await f(self, *args, **kwargs)
    #         else:
    #             logger.info(f"{self.event.sender} is not staff and tried executing staff command.")
    #             await send_text_to_room(
    #                 self.client, self.config.management_room_id,
    #                 f"User is not authorized to use this command",
    #             )
    #             return
    #     return wrapper

    ## Commands

    async def _echo(self):
        """Echo back the command's arguments"""
        response = " ".join(self.args)
        await send_text_to_room(self.client, self.room.room_id, response)

    async def _show_help(self):
        """Show the help text"""
        if not self.args:
            text = (
                "Hello, I am a support bot. Use `help commands` to view "
                "available commands."
            )
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        help_messages = {
            "message":commands_help.COMMAND_WRITE,
            "claimfor": commands_help.COMMAND_CLAIMFOR,
            "claim":commands_help.COMMAND_CLAIM,
            "raise":commands_help.COMMAND_RAISE,
            "close":commands_help.COMMAND_CLOSE,
            "reopen":commands_help.COMMAND_REOPEN,
            "opentickets":commands_help.COMMAND_OPEN_TICKETS,
            "openchats":commands_help.COMMAND_OPEN_CHATS,
            "activeticket":commands_help.COMMAND_ACTIVE_TICKET,
            "addstaff":commands_help.COMMAND_ADD_STAFF,
            "setupcommunicationsroom":commands_help.COMMAND_SETUP_COMMUNICATIONS_ROOM,
            "printroomstate":commands_help.COMMAND_PRINT_ROOM_STATE,
            "fetchroomstate":commands_help.COMMAND_FETCH_ROOM_STATE,
            "messageroom":commands_help.COMMAND_MESSAGE_ROOM,
            "chat":commands_help.COMMAND_CHAT,
            "forcecloseticket": commands_help.COMMAND_FORCE_CLOSE_TICKET,
            "forceclosechat": commands_help.COMMAND_FORCE_CLOSE_CHAT,
            "deleteticketroom": commands_help.COMMAND_DELETE_TICKET_ROOM,
            "deletechatroom": commands_help.COMMAND_DELETE_CHAT_ROOM,
        }
        help_messages["commands"] = ", ".join(list(help_messages.keys()))
        topic = self.args[0]
        text = help_messages.get(topic,"Unknown help topic!")
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )

    #TODO refactor direct messaging
    async def _message(self):
        """
        Write a m.text message to a room.
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow sending messages from the management room
            return

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_WRITE)
            return

        replaces = get_replaces(self.event)
        replaces_event_id = None
        if replaces:
            message = self.store.get_message_by_management_event_id(replaces)
            if message:
                replaces_event_id = message["event_id"]

        room = self.args[0]
        # Remove the command
        text = self.command[7:]
        # Remove the room
        text = text.replace(room, "", 1)
        # Strip the leading spaces
        text = text.strip()

        response = await send_text_to_room(self.client, room, text, False, replaces_event_id=replaces_event_id)

        if type(response) == RoomSendResponse and response.event_id:
            self.store.store_message(
                event_id=response.event_id,
                management_event_id=self.event.event_id,
                room_id=room,
            )
            if replaces_event_id:
                logger.info(f"Processed editing message in room {room}")
                await send_text_to_room(self.client, self.room.room_id, f"Message was edited in {room}")
            else:
                logger.info(f"Processed sending message to room {room}")
                await send_text_to_room(self.client, self.room.room_id, f"Message was delivered to {room}")
            return

        error_message = response if type(response == str) else getattr(response, "message", "Unknown error")
        await send_text_to_room(
            self.client, self.room.room_id, f"Failed to deliver message to {room}! Error: {error_message}",
        )

    async def _open_chats(self):
        """
        No args - List all open chats
        Arg provided - List all open chats assigned to staff member
        """
        chat_rep: ChatRepository = self.store.repositories.chatRep

        if len(self.args) == 1:
            staff = Staff.get_existing(self.store, self.args[0])
            if not staff:
                await send_text_to_room(
                    self.client, self.room.room_id, f"{self.args[0]} is not a staff member.",
                )
                return
            open_chats = chat_rep.get_open_chats_of_staff(staff.user_id)
        else:
            open_chats = chat_rep.get_open_chats()

        # Construct response array
        resp = [f"<p>{chat['chat_room_id']} - {chat['user_id']}</p>" for chat in open_chats]
        resp = "".join(resp)

        await send_text_to_room(
            self.client, self.room.room_id, f"Open chats: \n{resp}",
        )

    async def _open_tickets(self):
        """
        No args - List all open tickets
        Arg provided - List all open tickets assigned to staff member
        """
        ticket_rep: TicketRepository = self.store.repositories.ticketRep

        if len(self.args) == 1:
            staff = Staff.get_existing(self.store, self.args[0])
            if not staff:
                await send_text_to_room(
                    self.client, self.room.room_id, f"{self.args[0]} is not a staff member.",
                )
                return
            open_tickets = ticket_rep.get_open_tickets_of_staff(staff.user_id)
        else:
            open_tickets = ticket_rep.get_open_tickets()

        # Construct response array
        resp = [f"<p>{ticket['id']} - {ticket['ticket_name']} - {ticket['user_id']}</p>" for ticket in open_tickets]
        resp = "".join(resp)

        await send_text_to_room(
            self.client, self.room.room_id, f"Open tickets: \n{resp}",
        )

    async def _show_active_user_ticket(self):
        """
        Print active ticket of user
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_ACTIVE_TICKET)
            return

        user_id = self.args[0]

        user = User.get_existing(self.store, user_id)
        if not user:
            await send_text_to_room(
                self.client, self.room.room_id, f"User with ID {user_id} does not exist in DB",
            )
            return

        await send_text_to_room(
            self.client, self.room.room_id, f"{user.current_ticket_id}",
        )

    async def _show_active_user_chat(self):
        """
        Print active chat of user
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_ACTIVE_CHAT)
            return

        user_id = self.args[0]

        user = User.get_existing(self.store, user_id)
        if not user:
            await send_text_to_room(
                self.client, self.room.room_id, f"User with ID {user_id} does not exist in DB",
            )
            return

        await send_text_to_room(
            self.client, self.room.room_id, f"{user.current_chat_room_id}",
        )

    async def _add_staff(self):
        """
        Add staff
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow adding staff from the management room
            return

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_ADD_STAFF)
            return

        user_id = self.args[0]

        Staff.create_new(self.store, user_id)
        await send_text_to_room(
            self.client, self.room.room_id, f"{user_id} is now staff.",
        )

    async def _setup_communications_room(self):
        """
        Updates the communications room of a user. Creates one if needed.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_SETUP_COMMUNICATIONS_ROOM)
            return

        user_id = self.args[0]

        user = User.get_existing(self.store, user_id)
        if not user:
            # If we don't have the user details yet - create new instance
            user = User.create_new(self.store, user_id)

        room = find_private_msg(self.client, user_id)

        if room:
            user.update_communications_room(room.room_id)
            await send_text_to_room(
                self.client, self.room.room_id, f"Existing room found with ID {room.room_id}",
            )
            return

        username = get_username(self.client.user_id)
        if not username:
            await send_text_to_room(
                self.client, self.room.room_id, f"Invalid mxid {self.client.user_id}",
            )

        resp = await create_private_room(self.client, user_id, username)
        if isinstance(resp, RoomCreateResponse):
            user.update_communications_room(resp.room_id)
            await send_text_to_room(
                self.client, self.room.room_id,
                f"Created a new DM for user {user_id} with roomID: {resp.room_id}",
            )
        elif isinstance(resp, RoomCreateError):
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to create a new DM for user {user_id} with error: {resp.status_code}",
            )

    async def _fetch_room_state(self):
        """
        Fetches the room state of the provided room.
        """

        if len(self.args) < 4:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_FETCH_ROOM_STATE)
            return

        room_id = self.args[0]
        filterStr = self.args[1]
        full_state = self.args[2]
        since = self.args[3]
        
        if filterStr == "{}":
            filter = None
        else:
            filter = json.loads(filterStr)
            
        if full_state == "full":
            full_state = True
        else:
            full_state = False
            
        filter_json = json.dumps(filter, separators=(",", ":"))
            
        msg = f"Fetching {full_state} since {since} state of room: {room_id} with filter {filter} -- {filter_json}: \n\n"
        
        #resp = await self.client.room_get_state(room_id)
        resp = await filtered_sync(self.client, full_state=full_state, sync_filter=filter, since=since)
        if type(resp) == SyncResponse:
            msg += f"Received SyncResponse for room {room_id} : {resp}"
        elif type(resp) == SyncError:
            msg += f"Received SyncError for room {room_id}: {resp} - {resp.message} - {resp.transport_response} - {resp.transport_response.content} - {resp.transport_response.status_code}"
        else:
            msg += f"Received Unknown response for room {room_id}: {resp}"
        logger.info(msg)

        await send_text_to_room(
            self.client, self.room.room_id,
            msg,
        )
        
    async def __delete_room_state(self):
        """
        Deletes the room state of the provided room.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_DELETE_ROOM_STATE)
            return

        room_id = self.args[0]

        msg = ""
        if room_id in self.client.rooms:
            msg += "Deleting room from rooms list \n"
            del self.client.rooms[room_id]
        
        if room_id in self.client.invited_rooms:
            msg += "Deleting room from invited rooms list \n"
            del self.client.rooms[room_id]
        
        msg += "Command complete"

        logger.info(msg)

        await send_text_to_room(
            self.client, self.room.room_id,
            msg,
        )

        
    async def _message_room(self):
        """
        Sends text message to the provided room id.
        """

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_MESSAGE_ROOM)
            return

        room_id = self.args[0]
        to_send= " ".join(self.args[1:])
        
        msg = ""
        if not self.client.rooms.get(room_id, None):
            msg += f"Failed to retrieve room {room_id} details, creating task for awaiting room status and sending message later. \n"
            task = (self.client.callbacks._message, room_id, self.event.room_id, self.event, int(time.time()))
            # Add the task to the room queue to be sent when room is loaded
            self.client.callbacks.rooms_pending[task[1]].append(task)
        else:
            response = await send_text_to_room(self.client,
                                       room_id, to_send,
                                       False
                                    )
            if type(response) == RoomSendResponse and response.event_id:
                msg += f"Message relayed to room {room_id}"
            else:
                msg += f"Failed to relay message to room {room_id}, dropping message"
        
        logger.info(msg)
        await send_text_to_room(
            self.client, self.room.room_id,
            msg,
            markdown_convert = True
        )
                
    async def _print_room_state(self):
        """
        Fetches the room state of the provided room.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_PRINT_ROOM_STATE)
            return

        room_id = self.args[0]
        msg = f"Current known state of room: {room_id}: \n"
        if room_id in self.client.rooms:
            msg += "Room is present in room list \n"
            room = self.client.rooms[room_id]
            msg += f"Room name is: {room.name} | Creator: {room.creator} \n"
            msg += f"Room users: {room.users.keys()} \n"
            msg += f"Room invited users: {room.invited_users.keys()} \n"
        else:
            msg += "Room is not present in room list \n"
        
        if room_id in self.client.encrypted_rooms:
            msg += "Room is present in encrypted room list \n"
        else:
            msg += "Room is not present in encrypted room list \n"
            
        if room_id in self.client.invited_rooms:
            msg += "Room is present in invited room list \n"
        else:
            msg += "Room is not present in invited room list \n"
        
        logger.info(msg)        

        await send_text_to_room(
            self.client, self.room.room_id,
            msg,
            markdown_convert = True
        )
        
            
    async def _copy_incoming_events(self, ticket:Ticket):
        incomingEvents = IncomingEvent.get_incoming_events(self.store, ticket.user_id)
        for event in incomingEvents:
            
            # Delete old paired events to prevent original message being tied to different clones
            EventPair.delete_event(self.store, event.room_id, event.event_id)
            
            resp = await self.client.room_get_event(event.room_id, event.event_id)
            if isinstance(resp, RoomGetEventResponse):
                if isinstance(resp.event, (RoomMessageText, RoomMessageNotice, RoomMessageFormatted)):
                    task = (self.client.callbacks._message, ticket.ticket_room_id, event.room_id, resp.event, int(time.time()))
                elif isinstance(resp.event, (RoomMessageMedia, RoomEncryptedMedia)):
                    task = (self.client.callbacks._media, ticket.ticket_room_id, event.room_id, resp.event, int(time.time()))
                else:
                    continue
                
                # 0 - task method
                # 1 - room that is blocking the task
                # 2 - room the event originated from
                # 3 - the event itself
                
                if task[1] in self.client.rooms:
                    await task[0](self.client.rooms[task[2]], task[3])
                else:
                    self.client.callbacks.rooms_pending[task[1]].append(task)
            else:
                msg = f"Failed to get event {event.event_id} from user {event.user_id} in room {event.room_id}. Event was not copied to new room."
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
        
        # Delete the events
        IncomingEvent.delete_user_incoming_events(self.store, ticket.user_id)

    async def _raise_ticket(self):
        """
        Staff raise a ticket for a user.
        """

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_RAISE)
            return

        user_id = self.args[0]
        # Remove the command
        text = self.command[7:]
        # Remove the user_id
        text = text.replace(user_id, "", 1)
        # Strip the leading spaces
        text = text.strip()

        # Find User by user_id
        user = User.get_existing(self.store, user_id)

        if not user:
            msg = f"Failed to raise Ticket: {user_id} has not texted the bot yet. \"" \
                  f"You can try finding/creating a new DM with user using !setupcommunicationsroom"
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return

        # Raise a new ticket
        if text:
            ticket = Ticket.create_new(self.store, user.user_id, text)
        else:
            ticket = Ticket.create_new(self.store, user.user_id)

        if ticket:
            user.update_current_ticket_id(ticket.id)

            msg = f"Raised Ticket #{ticket.id} {ticket.ticket_name} for {ticket.user_id}"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            if self.room.room_id != self.config.management_room_id:
                await send_text_to_room(self.client, self.config.management_room_id,msg,)
        else:
            msg = f"Failed to raise Ticket. Index was not created in DB."
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return

        # Create a room for this ticket and invite staff to it
        response = await ticket.create_ticket_room(self.client, [self.handler.staff.user_id])
        if isinstance(response, RoomCreateResponse):
            logger.info(f"Created a Ticket room {response.room_id} successfully for ticket id {ticket.id}")
        else:
            msg = f"Failed to create a room for ticket id {ticket.id}"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return
          
        # Claim Ticket for the staff
        ticket.claim_ticket(self.handler.staff.user_id)

        # Invite staff to Ticket room
        # response = await ticket.invite_to_ticket_room(self.client, self.handler.staff.user_id)

        # Send user messages sent to management room to ticket room.
        await self._copy_incoming_events(ticket)

        #if isinstance(response, RoomInviteResponse):
        #    logger.info(f"Invited staff {self.handler.staff.user_id} to room {ticket.ticket_room_id}")
        #else:
        #    msg = f"Failed to invite staff {self.handler.staff.user_id} to room {ticket.ticket_room_id}"
        #    logger.info(msg)
        #    await send_text_to_room(
        #        self.client, self.room.room_id, msg,
        #    )
        #    return

    async def _chat(self):
        """
        Staff create a chat with user.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CHAT)
            return

        user_id = self.args[0]

        # Find User by user_id
        user = User.get_existing(self.store, user_id)

        if not user:
            username = get_username(user_id)
            if not username:
                msg = f"Failed to chat with {user_id}, user does not exist"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                return
            else:
                user = User.create_new(self.store, user_id)

        # Fetch existing or create new Chat for user:
        if user.current_chat_room_id:
            chat = Chat.get_existing(self.store, user.current_chat_room_id)
            if not chat:
                msg = f"Unable to find chat with ID {user.current_chat_room_id} in DB of {user_id}"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                return
        else:
            response = await Chat.create_new(self.store, self.client, user.user_id)
            if isinstance(response, RoomCreateError):
                msg = f"Failed to create Room: {response.status_code}"
                logger.error(msg)
                await send_text_to_room(
                    self.client, self.room.room_id, msg,
                )
                return
            elif isinstance(response, Exception):
                logger.error(f"Failed to store Chat with error: {response}")
                return

            chat = response
            user.update_current_chat_room_id(chat.chat_room_id)

            msg = f"Created Chat {chat.chat_room_id} for {chat.user_id}"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            if self.room.room_id != self.config.management_room_id:
                await send_text_to_room(self.client, self.config.management_room_id, msg,)

        # Claim Chat for staff
        chat.claim_chat(self.handler.staff.user_id)

        # Invite staff to the Chat room
        response = await chat.invite_to_chat_room(self.client, self.handler.staff.user_id)

        if isinstance(response, RoomInviteResponse):
            logger.info(f"Invited staff {self.handler.staff.user_id} to chat room {chat.chat_room_id}")
        else:
            msg = f"Failed to invite staff {self.handler.staff.user_id} to chat room {chat.chat_room_id} - {response.message}"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return

    async def _close_room(self):
        if self.handler.room_type == RoomType.ChatRoom:
            await self._close_chat()
        else:
            await self._close_ticket()

    async def _close_chat(self):
        """
        Staff close the current Chat.
        """

        chat:Chat = Chat.find_chat_of_room(self.store, self.room)
        if not chat:
            msg = f"Could not find Chat of room {self.room.room_id} to close"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
            return
        
        resp = await close_chat(self.client, self.store, chat.chat_room_id, self.config.matrix_logging_room)
        if isinstance(resp, ErrorResponse):
                msg = f"Failed to forcefully close Chat {chat.chat_room_id}: {resp.message}"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg)

    async def _force_close_ticket(self):
        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_FORCE_CLOSE_TICKET)
            return
        
        ticket_id = self.args[0]
        if not ticket_id.isnumeric():
            err = f"Ticket ID must be a whole number"
            logger.warning(err)
            await send_text_to_room(self.client, self.room.room_id, err,)
            return

        ticket_id = int(ticket_id)
        
        ticket:Ticket = Ticket.get_existing(self.store, ticket_id)
        if not ticket:
            msg = f"Could not find Ticket with ticket id {ticket_id} to forcefully close"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
            return
        else:
            resp = await close_ticket(self.client, self.store, ticket_id, self.config.matrix_logging_room)
            if isinstance(resp, ErrorResponse):
                msg = f"Failed to forcefully close Ticket {ticket_id}: {resp.message}"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg)

    async def _force_close_chat(self):
        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_FORCE_CLOSE_CHAT)
            return
        
        chat_room_id = self.args[0]
        
        chat:Chat = Chat.get_existing(self.store, chat_room_id)
        if not chat:
            msg = f"Could not find Chat with chat room id {chat_room_id} to forcefully close"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
        else:
            resp = await close_chat(self.client, self.store, chat.chat_room_id, self.config.matrix_logging_room)
            if isinstance(resp, ErrorResponse):
                msg = f"Failed to forcefully close Chat {chat.chat_room_id}: {resp.message}"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg)
                
    async def _close_ticket(self) -> None:
        """
        Staff close the current ticket.
        """

        ticket_id = Ticket.get_ticket_id_from_room_id(self.store, self.room.room_id)
        if not ticket_id:
            err = f"Could not find Ticket with ticket room {self.room.room_id} to close"
            logger.warning(err)
            await send_text_to_room(self.client, self.room.room_id, err,)
            return
        else:
            resp = await close_ticket(self.client, self.store, ticket_id, self.config.management_room_id)
            if isinstance(resp, ErrorResponse):
                await send_text_to_room(self.client, self.room.room_id, f"Failed to close Ticket: {resp.message}")
    
    async def __delete_ticket_room(self) -> None:
        """
        Staff delete the Ticket room.
        """
        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_DELETE_TICKET_ROOM)
            return
        
        ticket_id = self.args[0]
        
        if not ticket_id.isnumeric():
            err = f"Ticket ID must be a whole number"
            logger.warning(err)
            await send_text_to_room(self.client, self.room.room_id, err,)
            return

        ticket_id = int(ticket_id)
        
        ticket:Ticket = Ticket.get_existing(self.store, ticket_id)
        if not ticket:
            msg = f"Could not find Ticket with ticket id {ticket_id} to delete room of"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
        else:
            resp = await delete_ticket_room(self.client, self.store, ticket_id, self.config.matrix_logging_room)
            if isinstance(resp, ErrorResponse):
                await send_text_to_room(self.client, self.room.room_id, f"Failed to delete Ticket: {resp.message}")

    async def __delete_chat_room(self) -> None:
        """
        Staff delete chat room by room id.
        """
        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_DELETE_CHAT_ROOM)
            return
        
        room_id = self.args[0]
        chat_room_id = Chat.get_chat_room_id_from_room_id(self.store, room_id)
        
        if not chat_room_id:
            msg = f"Chat with room id {room_id} does not exist"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
            
        chat:Chat = Chat.get_existing(self.store, chat_room_id)
        if not chat:
            msg = f"Could not find Chat with chat room id {chat_room_id} to delete room of"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
        else:
            resp = await delete_chat_room(self.client, self.store, chat_room_id, self.config.matrix_logging_room)
            if isinstance(resp, ErrorResponse):
                await send_text_to_room(self.client, self.room.room_id, f"Failed to delete Chat: {resp.message}")
    
    async def __delete_user_room(self) -> None:
        """
        Staff delete user room by room id.
        """
        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_DELETE_USER_ROOM)
            return
        
        room_id = self.args[0]
        
        chat_room_id = Chat.get_chat_room_id_from_room_id(self.store, room_id)
        ticket_id = Ticket.get_ticket_id_from_room_id(self.store, room_id)
        
        if not chat_room_id and not ticket_id:
            msg = f"Room is neither a  not find Ticket with ticket id {ticket_id} to delete room of"
        ticket:Ticket = Ticket.get_existing(self.store, ticket_id)
        if not ticket:
            msg = f"Could not find Ticket with ticket id {ticket_id} to delete room of"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
        else:
            resp = await delete_ticket_room(self.client, self.store, ticket_id, self.config.matrix_logging_room)
            if isinstance(resp, ErrorResponse):
                msg = f"Failed to delete Ticket {ticket_id}: {resp.message}"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg)


    async def _reopen_ticket(self) -> None:
        """
        Staff reopen the current ticket, or specify and be reinvited to it.
        """

        if len(self.args) > 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_REOPEN)
            return

        ticket_id = None
        # Find ticket by room or provided ID
        if len(self.args) == 0:
            ticket_id = Ticket.get_ticket_id_from_room_id(self.store, self.room.room_id)
            if not ticket_id:
                err = TicketNotFound(ticket_id)
                logger.warning(err)
                await send_text_to_room(self.client, self.room.room_id, err.message,)
                return
        else:
            ticket_id = self.args[0]
            if not ticket_id.isnumeric():
                err = f"Ticket ID must be a whole number"
                logger.warning(err)
                await send_text_to_room(self.client, self.room.room_id, err,)
                return

            ticket_id = int(ticket_id)
        
        resp = await reopen_ticket(self.client, self.store, ticket_id, self.config.management_room_id)
        if isinstance(resp, ErrorResponse):
            msg = f"Failed to reopen Ticket {ticket_id}: {resp.message}"
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg)
            
    async def _claim(self):
        """
        Staff claim a ticket.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CLAIM)
            return

        ticket_id = self.args[0]

        
        resp = await claim(self.client, self.store, self.handler.staff.user_id, ticket_id)
        if isinstance(resp, ErrorResponse):
            msg = f"Failed to claim Ticket {ticket_id}: {resp.message}"
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg)
                
    async def _claimfor(self):
        """
        Staff claim a ticket for support.
        """

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CLAIMFOR)
            return

        user_id = self.args[0]
        ticket_id = self.args[1]

        resp = await claimfor(self.client, self.store, user_id, ticket_id)
        if isinstance(resp, ErrorResponse):
            msg = f"Failed to claimfor Ticket {ticket_id}: {resp.message}"
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg)

    

async def unassign_staff_from_ticket(client: AsyncClient, store: Storage, ticket_id: str, user_ids: [str]) -> Optional[ErrorResponse]:
    ticket:Ticket = Ticket.get_existing(store, ticket_id)
    if not ticket:
        return TicketNotFound(ticket_id)
    
    for user_id in user_ids:
        ticket.unassign_staff(user_id)
        resp = await kick_from_room(
                    client, user_id, ticket.ticket_room_id
                )
        if isinstance(resp, RoomKickError):
            logger.warning(f"Failed to kick user {user_id} from ticket ID: {ticket.id} in room {ticket.ticket_room_id}")

async def unassign_staff_from_chat(client: AsyncClient, store: Storage, chat_room_id: str, user_ids: [str]) -> Optional[ErrorResponse]:
    chat:Chat = Chat.get_existing(store, chat_room_id)
    if not chat:
        return ChatNotFound(chat_room_id)
    
    for user_id in user_ids:
        chat.unassign_staff(user_id)
        resp = await kick_from_room(
                    client, user_id, chat.chat_room_id
                )
        if isinstance(resp, RoomKickError):
            logger.warning(f"Failed to kick user {user_id} from chat {chat_room_id}")
    
    
async def claim(client: AsyncClient, store: Storage, staff_user_id: str, ticket_id:str) -> Optional[ErrorResponse]:
        """
        Staff claim a ticket.
        """
        # Get ticket by id
        ticket = Ticket.get_existing(store, int(ticket_id))

        if not ticket:
            return TicketNotFound(ticket_id)

        # Claim Ticket for the staff
        ticket.claim_ticket(staff_user_id)

        logger.debug(f"Inviting user {staff_user_id} to ticket room {ticket.ticket_room_id}")

        # Invite staff to Ticket room
        response = await ticket.invite_to_ticket_room(client, staff_user_id)

        if isinstance(response, RoomInviteResponse):
            try:
                resp = await send_shared_history_keys(client, ticket.ticket_room_id, [staff_user_id])
                if isinstance(resp, ErrorResponse):
                    return resp
                logger.debug(f"Invited staff to Ticket room successfully")
            except Exception as e:
                return ErrorResponse(f"Failed to share keys with user {staff_user_id} {e}", Errors.EXCEPTION)
        else:
            return ErrorResponse(f"Failed to invite {staff_user_id} to Ticket room {ticket.ticket_room_id}: {response.message}", Errors.ROOM_INVITE)

async def chat_claim(client: AsyncClient, store: Storage, staff_user_id: str, chat_room_id:str) -> Optional[ErrorResponse]:
        """
        Staff claim a chat.
        """
        # Get chat by chat room id
        chat = Chat.get_existing(store, chat_room_id)

        if not chat:
            return ChatNotFound(chat_room_id)

        # Claim Chat for the staff
        chat.claim_chat(staff_user_id)

        logger.debug(f"Inviting user {staff_user_id} to chat room {chat.chat_room_id}")

        # Invite staff to Chat room
        response = await chat.invite_to_chat_room(client, staff_user_id)

        if isinstance(response, RoomInviteResponse):
            try:
                resp = await send_shared_history_keys(client, chat.chat_room_id, [staff_user_id])
                if isinstance(resp, ErrorResponse):
                    return resp
                logger.debug(f"Invited staff to Chat room successfully")
            except Exception as e:
                return ErrorResponse(f"Failed to share keys with user {staff_user_id} {e}", Errors.EXCEPTION)
        else:
            return ErrorResponse(f"Failed to invite {staff_user_id} to chat room {chat.chat_room_id}: {response.message}", Errors.ROOM_INVITE)

async def reopen_ticket(client: AsyncClient, store: Storage, ticket_id: str, management_room_id:str) -> Optional[ErrorResponse]:
        """
        Staff reopen the current ticket, or specify and be reinvited to it.
        """
        
        if not isinstance(ticket_id, int):
            return ErrorResponse(f"Ticket id must be of type int", Errors.EXCEPTION)
        
        ticket = Ticket.get_existing(store, ticket_id)
        
        if not ticket:
            return TicketNotFound(ticket_id)

        current_user_ticket_id = ticket.find_user_current_ticket_id()
        if current_user_ticket_id is not None:
            return ErrorResponse(f"User already has Ticket open with ID {current_user_ticket_id} close it first to reopen this Ticket.", Errors.INVALID_ROOM_STATE)
        if ticket.status == TicketStatus.CLOSED:
            ticket.set_status(TicketStatus.OPEN)
            ticket.userRep.set_user_current_ticket_id(ticket.user_id, ticket.id)

            msg = f"Reopened Ticket {ticket.id}"
            logger.info(msg)
            await send_text_to_room(client, management_room_id, msg,)
            await send_text_to_room(client, ticket.ticket_room_id, msg,)

            # Invite staff to the ticket room if not joined already
            # Invite all assigned support to the room
            support_users = ticket.get_assigned_support() + ticket.get_assigned_staff()

            for staff in support_users:
                resp = await invite_to_room(client, staff, ticket.ticket_room_id)

                if isinstance(resp, RoomInviteResponse):
                    try:
                        resp = await send_shared_history_keys(client, ticket.ticket_room_id, [staff])
                        if isinstance(resp, ErrorResponse):
                            logger.warning(f"Failed to share room keys of {ticket.ticket_room_id} with {staff}: {resp}")
                    except Exception as e:
                        logger.warning(e)
                else:
                    logger.warning(f"Failed to invite {staff} to room {ticket.ticket_room_id}: {resp}")
        else:
            return ErrorResponse(f"Ticket {ticket.id} is {ticket.status}, not in CLOSED state.", Errors.INVALID_ROOM_STATE)

async def claimfor(client: AsyncClient, store: Storage, user_id:str, ticket_id:str) -> Optional[ErrorResponse]:
        """
        Staff claim a ticket for support.
        """

        # Get ticket by id
        ticket = Ticket.get_existing(store, int(ticket_id))

        if not ticket:
            return TicketNotFound(ticket_id)
        
        support = Support.get_existing(store, user_id)
        
        if not support:
            logger.info(f"Creating new support user for {user_id}.")
            support = Support.create_new(store, user_id)

        # Claim Ticket for the support user
        ticket.claimfor_ticket(support.user_id)

        logger.debug(f"Inviting user {support.user_id} to ticket room {ticket.ticket_room_id}")

        # Invite support to Ticket room
        response = await ticket.invite_to_ticket_room(client, support.user_id)

        if isinstance(response, RoomInviteResponse):
            try:
                resp = await send_shared_history_keys(client, ticket.ticket_room_id, [support.user_id])
                if isinstance(resp, ErrorResponse):
                    return resp
            except Exception as e:
                return ErrorResponse(e, Errors.EXCEPTION)
        else:
            return ErrorResponse(f"Failed to invite {support.user_id} to Ticket room {ticket.ticket_room_id}: {response.message}", Errors.ROOM_INVITE)

async def chat_claimfor(client: AsyncClient, store: Storage, user_id:str, chat_room_id:str) -> Optional[ErrorResponse]:
        """
        Staff claim a chat for support.
        """

        # Get ticket by id
        chat = Chat.get_existing(store, chat_room_id)

        if not chat:
            return ChatNotFound(chat_room_id)
        
        support = Support.get_existing(store, user_id)
        
        if not support:
            logger.info(f"Creating new support user for {user_id}.")
            support = Support.create_new(store, user_id)

        # Claim Ticket for the support user
        chat.claimfor_ticket(support.user_id)

        logger.debug(f"Inviting user {support.user_id} to chat room {chat.chat_room_id}")

        # Invite support to Chat room
        response = await chat.invite_to_chat_room(client, support.user_id)

        if isinstance(response, RoomInviteResponse):
            try:
                resp = await send_shared_history_keys(client, chat.chat_room_id, [support.user_id])
                if isinstance(resp, ErrorResponse):
                    return resp
            except Exception as e:
                return ErrorResponse(e, Errors.EXCEPTION)
        else:
            return ErrorResponse(f"Failed to invite {support.user_id} to Chat room {chat.chat_room_id}: {response.message}", Errors.ROOM_INVITE)

async def close_ticket(client: AsyncClient, store: Storage, ticket_id:int, management_room_id:str) -> Optional[ErrorResponse]:
        """
        Staff close the current ticket of provided ticket id.
        """

        if not isinstance(ticket_id, int):
            return ErrorResponse(f"Ticket id must be of type int", Errors.EXCEPTION)
        
        ticket:Ticket = Ticket.get_existing(store, ticket_id)
        if not ticket:
            return TicketNotFound(ticket_id)
        else:
            if ticket.status == TicketStatus.OPEN:
                ticket.set_status(TicketStatus.CLOSED)

                current_user_ticket_id = ticket.find_user_current_ticket_id()
                if current_user_ticket_id == ticket.id:
                    ticket.userRep.set_user_current_ticket_id(ticket.user_id, None)

                msg = f"Closed Ticket {ticket.id}"
                logger.info(msg)
                await send_text_to_room(client, ticket.ticket_room_id, msg,)
                await send_text_to_room(client, management_room_id, msg,)

                # Kick all support from the room
                support_users = ticket.get_assigned_support()
                for support in support_users:
                    await kick_from_room(
                    client, support, ticket.ticket_room_id
                )
                
                # Kick staff from room after close
                staff_users = ticket.get_assigned_staff()
                for staff in staff_users:
                    await kick_from_room(
                        client, staff, ticket.ticket_room_id
                    ) 
            else:
                return ErrorResponse(f"Ticket {ticket.id} is already closed", Errors.INVALID_ROOM_STATE)
            
async def close_chat(client: AsyncClient, store: Storage, chat_room_id:str, management_room_id:str) -> Optional[ErrorResponse]:
        """
        Staff close the chat of provided chat room id.
        """

        chat:Chat = Chat.get_existing(store, chat_room_id)
        if not chat:
            return ChatNotFound(chat_room_id)
        else:
            if chat.status == ChatStatus.OPEN:
                current_user_chat_room_id = chat.find_user_current_chat_room_id()
                if current_user_chat_room_id == chat.chat_room_id:
                    chat.userRep.set_user_current_chat_room_id(chat.user_id, None)

                chat.set_status(ChatStatus.CLOSED)
                msg = f"Closed Chat {chat.chat_room_id}"
                logger.info(msg)
                await send_text_to_room(client, chat.chat_room_id, msg,)
                await send_text_to_room(client, management_room_id, msg,)

                # Kick all support from the room
                support_users = chat.get_assigned_support()
                for support in support_users:
                    await kick_from_room(
                    client, support, chat.chat_room_id
                )
                
                # Kick staff from room after close
                staff_users = chat.get_assigned_staff()
                for staff in staff_users:
                    await kick_from_room(
                        client, staff, chat.chat_room_id
                    ) 
                    
                # Auto-delete room after close.
                room:MatrixRoom = client.rooms.get(chat.chat_room_id, None)
                if not room:
                    return ErrorResponse(f"Chat {chat.chat_room_id} not found in local state, delete the room manually.", Errors.INVALID_ROOM_STATE)
                    
                if room.joined_count == 1 and room.invited_count == 0:
                    # Delete chat room
                    response = await delete_room(client, room.room_id)
                    if isinstance(response, ErrorResponse):
                        msg = f"Failed to leave room: {response}"
                        logger.error(msg)
                        await send_text_to_room(client, management_room_id, msg,)
                    else:
                        chat.set_status(ChatStatus.DELETED)
                        msg = f"Deleted Chat {room.room_id}."
                        logger.info(msg)
                        await send_text_to_room(client, management_room_id, msg,)
                else:
                    logger.info(f"Added Chat room {room.room_id} to marked for deletion queue.")
                    client.callbacks.rooms_marked_for_deletion[room.room_id] = room.room_id
            else:
                return ErrorResponse(f"Chat {chat.chat_room_id} is already closed", Errors.INVALID_ROOM_STATE)

async def delete_ticket_room(client: AsyncClient, store: Storage, ticket_id:int, management_room_id:str) -> Optional[ErrorResponse]:
        """
        Staff delete the Ticket room.
        """
        
        if not isinstance(ticket_id, int):
            return ErrorResponse(f"Ticket id must be of type int", Errors.EXCEPTION)
        
        ticket:Ticket = Ticket.get_existing(store, ticket_id)
        if not ticket:
            return TicketNotFound(ticket_id)
        else:
            if ticket.status == TicketStatus.DELETED:
                return ErrorResponse(f"Ticket {ticket.id} room already deleted", Errors.LOGIC_CHECK)
            
            if ticket.status != TicketStatus.CLOSED:
                return ErrorResponse(f"Ticket {ticket.id} room must be in CLOSED state to be deleted", Errors.LOGIC_CHECK)
            
            if ticket.ticket_room_id in client.rooms:
                ticket_room:MatrixRoom = client.rooms[ticket.ticket_room_id]
            else:
                return ErrorResponse(f"Ticket {ticket.id} room {ticket.ticket_room_id} not found in local state", Errors.INVALID_ROOM_STATE)
            
            if ticket_room.joined_count > 1:
                return ErrorResponse(f"Ticket {ticket.id} room {ticket.ticket_room_id} has more than one user: {', '.join(ticket_room.users.keys())}", Errors.LOGIC_CHECK)
                
            if ticket_room.invited_count != 0:
                return ErrorResponse(f"Ticket {ticket.id} room {ticket.ticket_room_id} has pending invites: {', '.join(ticket_room.invited_users.keys())}", Errors.LOGIC_CHECK)

            response = await delete_room(client, ticket.ticket_room_id)
            if isinstance(response, ErrorResponse):
                logger.error(f"Failed to leave room: {response}")
                return response
            else:
                ticket.set_status(TicketStatus.DELETED)

                msg = f"Deleted Ticket {ticket.id} room {ticket.ticket_room_id}"
                logger.info(msg)
                await send_text_to_room(client, management_room_id, msg,)
    
async def delete_chat_room(client: AsyncClient, store: Storage, chat_room_id:str, management_room_id:str) -> Optional[ErrorResponse]:
        """
        Staff delete the Chat room.
        """

        chat:Chat = Chat.get_existing(store, chat_room_id)
        if not chat:
            return ChatNotFound(ticket_id)
        else:
            current_user_chat_room_id = chat.find_user_current_chat_room_id()

        if current_user_chat_room_id == chat.chat_room_id:
            return ErrorResponse(f"Chat room {chat.chat_room_id} still assigned to chat user {chat.user_id}", Errors.LOGIC_CHECK)
        
        if chat.chat_room_id in client.rooms:
            chat_room:MatrixRoom = client.rooms[chat.chat_room_id]
        else:
            return ErrorResponse(f"Chat {chat.chat_room_id} room not found in local state", Errors.INVALID_ROOM_STATE)
        
        if chat_room.joined_count > 1:
            return ErrorResponse(f"Chat {chat.chat_room_id} room has more than one user: {', '.join(chat_room.users.keys())}", Errors.LOGIC_CHECK)
            
        if chat_room.invited_count != 0:
            return ErrorResponse(f"Chat {chat.chat_room_id} room has pending invites: {', '.join(chat_room.invited_users.keys())}", Errors.LOGIC_CHECK)
        
        response = await delete_room(client, chat_room.room_id)
        if isinstance(response, ErrorResponse):
            logger.error(f"Failed to leave room: {response}")
            return response
        else:
            chat.set_status(ChatStatus.DELETED)
            msg = f"Deleted Chat {chat_room_id} room"
            logger.info(msg)
            await send_text_to_room(client, management_room_id, msg,)

async def unassign_support_from_ticket(client: AsyncClient, store: Storage, ticket_id: str, user_ids: [str]) -> Optional[ErrorResponse]:
        ticket:Ticket = Ticket.get_existing(store, ticket_id)
        if not ticket:
            return TicketNotFound(ticket_id)
        
        for user_id in user_ids:
            ticket.unassign_support(user_id)
            resp = await kick_from_room(
                        client, user_id, ticket.ticket_room_id
                    )
            if isinstance(resp, RoomKickError):
                logger.warning(f"Failed to kick user {user_id} from ticket ID: {ticket.id} in room {ticket.room_id}")

async def fetch_ticket_room_messages(client: AsyncClient, store: Storage, ticket_id: str, limit=10, start:str = '', end:str = '') -> Optional[ErrorResponse]:
    ticket:Ticket = Ticket.get_existing(store, ticket_id)
    if not ticket:
        return TicketNotFound(ticket_id)
    
    resp = await get_room_messages(client, ticket.ticket_room_id, limit, start, end)
    return resp