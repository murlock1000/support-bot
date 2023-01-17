import logging

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomCreateResponse, RoomInviteResponse

from middleman import commands_help
from middleman.chat_functions import create_private_room, invite_to_room, send_text_to_room
from middleman.models.Repositories.TicketRepository import TicketStatus, TicketRepository
from middleman.models.Staff import Staff
from middleman.models.Ticket import Ticket
from middleman.models.User import User
from middleman.utils import get_replaces

logger = logging.getLogger(__name__)


class Command(object):
    def __init__(self, client, store, config, command, room, event, ticket:Ticket=None):
        """A command made by a user

        Args:
            client (nio.AsyncClient): The client to communicate to matrix with

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            command (str): The command and arguments

            room (nio.rooms.MatrixRoom): The room the command was sent in

            event (nio.events.room_events.RoomMessageText): The event describing the command
        """
        self.staff = None
        self.client = client
        self.store = store
        self.config = config
        self.command = command
        self.room = room
        self.event = event
        self.args = self.command.split()[1:]
        self.ticket = ticket

    async def process(self):
        """Process the command"""
        if self.command.startswith("echo"):
            await self._echo()
        elif self.command.startswith("help"):
            await self._show_help()
        elif self.command.startswith("message"):
            await self._message()
        elif self.command.startswith("claim"):
            await self._claim()
        elif self.command.startswith("raise"):
            await self._raise_ticket()
        elif self.command.startswith("close"):
            await self._close_ticket()
        elif self.command.startswith("reopen"):
            await self._reopen_ticket()
        elif self.command.startswith("opentickets"):
            await self._open_tickets()
        elif self.command.startswith("activeticket"):
            await self._show_active_user_ticket()
        elif self.command.startswith("addstaff"):
            await self._add_staff()
        else:
            await self._unknown_command()

    ## Decorators
    def with_staff(f):
        async def wrapper(self, *args, **kwargs):
            self.staff = Staff.get_existing(self.store, self.event.sender)
            if self.staff:
                await f(self, *args, **kwargs)
            else:
                logger.info(f"{self.event.sender} is not staff and tried executing staff command.")
                await send_text_to_room(
                    self.client, self.config.management_room_id,
                    f"User is not authorized to use this command",
                )
                return
        return wrapper

    ## Commands

    async def _echo(self):
        """Echo back the command's arguments"""
        response = " ".join(self.args)
        await send_text_to_room(self.client, self.room.room_id, response)

    @with_staff
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
            "commands":commands_help.AVAILABLE_COMMANDS,
            "message":commands_help.COMMAND_WRITE,
            "claim":commands_help.COMMAND_CLAIM,
            "raise":commands_help.COMMAND_RAISE,
            "close":commands_help.COMMAND_CLOSE,
            "reopen":commands_help.COMMAND_REOPEN,
            "opentickets":commands_help.COMMAND_OPEN_TICKETS,
            "activeticket":commands_help.COMMAND_ACTIVE_TICKET,
            "addstaff":commands_help.COMMAND_ADD_STAFF

        }
        topic = self.args[0]
        text = help_messages.get(topic,"Unknown help topic!")
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )

    @with_staff
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

    @with_staff
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

    @with_staff
    async def _show_active_user_ticket(self):
        """
        Print active ticket of user
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_ACTIVE_TICKET)
            return

        user_id = self.args[0]

        try:
            user = User(self.store, user_id)
        except IndexError as e:
            await send_text_to_room(
                self.client, self.room.room_id, f"{e.args[0]}",
            )
            return

        await send_text_to_room(
            self.client, self.room.room_id, f"{user.current_ticket_id}",
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

    @with_staff
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
            logger.warning(f"Failed to raise Ticket: {user} has not texted the bot yet")
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to raise Ticket: {user} has not texted the bot yet",
            )
            return

        # Raise a new ticket
        if text:
            ticket = Ticket.create_new(self.store, user.user_id, text)
        else:
            ticket = Ticket.create_new(self.store, user.user_id)

        if ticket:
            user.update_current_ticket_id(ticket.id)
            logger.info(f"Raised Ticket #{ticket.id} {ticket.ticket_name} for {ticket.user_id}")
            await send_text_to_room(
                self.client, self.room.room_id, f"Raised Ticket #{ticket.id} {ticket.ticket_name} for {ticket.user_id}",
            )
            if self.room.room_id != self.config.management_room_id:
                await send_text_to_room(
                    self.client, self.config.management_room_id,
                    f"Raised Ticket #{ticket.id} {ticket.ticket_name} for {ticket.user_id}",
                )
        else:
            logger.warning(f"Failed to raise Ticket. Index was not created in DB.")
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to raise Ticket. Index was not created in DB.",
            )
            return

        # Create a room for this ticket
        response = await ticket.create_ticket_room(self.client)
        if isinstance(response, RoomCreateResponse):
            logger.info(f"Created a Ticket room {response.room_id} successfully for ticket id {ticket.id}")
        else:
            logger.info(f"Failed to create a room for ticket id {ticket.id}")
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to create a room for ticket id {ticket.id}",
            )
            return

        # Claim Ticket for the staff
        ticket.claim_ticket(self.staff.user_id)

        # Invite staff to Ticket room
        response = await ticket.invite_to_ticket_room(self.client, self.staff.user_id)

        if isinstance(response, RoomInviteResponse):
            logger.info(f"Invited staff {self.staff.user_id} to room {ticket.ticket_room_id}")
        else:
            logger.info(f"Failed to invite staff {self.staff.user_id} to room {ticket.ticket_room_id}")
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to invite staff {self.staff.user_id} to room {ticket.ticket_room_id}",
            )
            return

    @with_staff
    async def _close_ticket(self):
        """
        Staff close the current ticket.
        """

        ticket:Ticket = Ticket.find_ticket_of_room(self.store, self.room)
        if not ticket:
            logger.warning(f"Could not find Ticket with ticket room {self.room.room_id} to close")
            await send_text_to_room(
                self.client, self.room.room_id,
                f"Could not find Ticket room {self.room.room_id} to close",
            )
        else:
            if ticket.status != TicketStatus.CLOSED:
                ticket.set_status(TicketStatus.CLOSED)

                current_user_ticket_id = ticket.find_user_current_ticket_id()
                if current_user_ticket_id == ticket.id:
                    ticket.userRep.set_user_current_ticket_id(ticket.user_id, None)

                logger.info(f"Closed Ticket {ticket.id}")
                await send_text_to_room(
                    self.client, self.room.room_id,
                    f"Closed Ticket {ticket.id}",
                )
            else:
                logger.info(f"Ticket {ticket.id} is already closed")
                await send_text_to_room(
                    self.client, self.room.room_id,
                    f"Ticket {ticket.id} is already closed",
                )


    async def _reopen_ticket(self):
        """
        Staff reopen the current ticket.
        """

        ticket: Ticket = Ticket.find_ticket_of_room(self.store, self.room)
        if not ticket:
            logger.warning(f"Could not find Ticket with ticket room {self.room.room_id} to reopen")
            await send_text_to_room(
                self.client, self.room.room_id,
                f"Could not find Ticket room {self.room.room_id} to reopen",
            )
        else:
            current_user_ticket_id = ticket.find_user_current_ticket_id()
            if current_user_ticket_id is not None:
                logger.warning(f"User already has Ticket open with ID {current_user_ticket_id} close it first to reopen this Ticket.")
                await send_text_to_room(
                    self.client, self.room.room_id,
                    f"User already has Ticket open with ID {current_user_ticket_id} close it first to reopen this Ticket.",
                )
                return
            if ticket.status == TicketStatus.CLOSED:
                ticket.set_status(TicketStatus.OPEN)

                ticket.userRep.set_user_current_ticket_id(ticket.user_id, ticket.id)

                logger.info(f"Reopened Ticket {ticket.id}")
                await send_text_to_room(
                    self.client, self.room.room_id,
                    f"Reopened Ticket {ticket.id}",
                )
            else:
                logger.info(f"Ticket {ticket.id} is already open")
                await send_text_to_room(
                    self.client, self.room.room_id,
                    f"Ticket {ticket.id} is already open",
                )

    @with_staff
    async def _claim(self):
        """
        Staff claim a ticket.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CLAIM)
            return

        ticket_id = self.args[0]

        # Get ticket by id
        ticket = Ticket.get_existing(self.store, int(ticket_id))

        if not ticket:
            logger.warning(f"Ticket with ID {ticket_id} was not found.")
            await send_text_to_room(
                self.client, self.room.room_id, f"Ticket with ID {ticket_id} was not found.",
            )
            return

        # Claim Ticket for the staff
        ticket.claim_ticket(self.staff.user_id)

        logger.debug(f"Inviting user {self.staff.user_id} to ticket room {ticket.ticket_room_id}")

        # Invite staff to Ticket room
        response = await ticket.invite_to_ticket_room(self.staff.user_id)

        if isinstance(response, RoomInviteResponse):
            logger.debug(f"Invited staff to Ticket room successfully")
        else:
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to invite {self.staff.user_id} to Ticket room {ticket.ticket_room_id}: {response.message}",
            )
