import logging
from typing import Callable

from middleman.models.Chat import Chat
from middleman.models.Repositories.TicketRepository import TicketStatus
from middleman.models.Ticket import Ticket
from middleman.models.User import User

logger = logging.getLogger(__name__)

from middleman.chat_functions import send_text_to_room, find_private_msg
from middleman.handlers.EventStateHandler import LogLevel, EventStateHandler


class MessagingHandler(object):
    def __init__(self, handler: EventStateHandler):
        self.client = handler.client
        self.store = handler.store
        self.config = handler.config
        self.room = handler.room
        self.event = handler.event
        self.handler = handler

    # Message in Ticket room business logic, return False on failure.
    async def handle_ticket_message(self) -> bool:

        if not self.handler.ticket:
            msg = f"Ticket for room {self.room.room_id} with name {self.room.name} not found."
            await self.handler.message_room(msg, LogLevel.ERROR)
            return False

        # Check if ticket is not closed
        if self.handler.ticket.status == TicketStatus.CLOSED:
            msg = f"Skipping message, since Ticket is closed. Reopen it first."
            await self.handler.message_room(msg, LogLevel.DEBUG)
            return False

        # Find user related to ticket
        self.handler.update_state_user(self.handler.ticket.user_id)

        # Check if this is the active ticket
        if self.handler.user.current_ticket_id != self.handler.ticket.id:
            msg = f"Skipping message, there are multiple open Tickets and this Ticket is not active \
                        ({self.handler.user.current_ticket_id} is active). First close \
                        {self.handler.user.current_ticket_id} and \
                        then reopen this Ticket."
            await self.handler.message_room(msg, LogLevel.DEBUG)
            return False

        # Check if a Chat with user does not exist
        if self.handler.user.current_chat_room_id:
            msg = f"Skipping message, there is a Chat room open ({self.handler.user.current_chat_room_id} \
            is active). First close it or convert to ticket with !toticket <ticket name>"
            await self.handler.message_room(msg, LogLevel.DEBUG)
            return False

        # Find user communications room to relay message to
        if not await self.find_communications_room(self.handler.ticket.user_id):
            return False

        return True

    # Message in Chat room business logic, return False on failure.
    async def handle_chat_message(self) -> bool:

        if not self.handler.chat:
            msg = f"Chat of room {self.room.room_id} not found."
            await self.handler.message_room(msg, LogLevel.ERROR)
            return False

        # Find user related to chat
        self.handler.update_state_user(self.handler.chat.user_id)

        # Check if a Ticket for user does not exist
        if self.handler.user.current_ticket_id:
            msg = f"Skipping message, there is a Ticket open (#{self.handler.user.current_ticket_id} \
                    is active). First close it, then chat."
            await self.handler.message_room(msg, LogLevel.DEBUG)
            return False

        # Find user communications room to relay message to
        if not await self.find_communications_room(self.handler.chat.user_id):
            return False
        return True

    async def setup_relay(self) -> str:
        # Find user from event
        if not self.handler.find_state_user():
            # If we don't have the user details yet - create new instance
            self.handler.create_state_user()

        # Update the communications channel to this room
        if self.handler.user.room_id != self.room.room_id:
            self.handler.user.update_communications_room(self.room.room_id)

        # Handle different relaying scenarios
        if self.handler.user.current_ticket_id:
            self.handler.update_state_ticket(self.handler.user.current_ticket_id)
            return self.handler.ticket.ticket_room_id
        elif self.handler.user.current_chat_room_id:
            self.handler.update_state_chat(self.handler.user.current_chat_room_id)
            return self.handler.chat.chat_room_id
        else:
            return self.config.management_room

    async def find_communications_room(self, user_id) -> bool :
        if not self.handler.user.room_id:
            room = find_private_msg(self.client, user_id)
            if not room:
                msg = f"User {self.handler.user.user_id} does not have a valid communications channel. \
                        The user must write to the bot first or create one with !setupcommunicationsroom."
                await self.handler.message_room(msg, LogLevel.WARNING)
                return False
            else:
                self.handler.user.update_communications_room(room.room_id)
        return True
