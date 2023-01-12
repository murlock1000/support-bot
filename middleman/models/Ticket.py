from nio import AsyncClient, RoomCreateResponse, RoomInviteResponse, MatrixRoom, Response

from middleman.chat_functions import invite_to_room, create_room, send_text_to_room
from middleman.models.Repositories.TicketRepository import TicketStatus, TicketRepository
from middleman.models.Repositories.UserRepository import UserRepository
from middleman.storage import Storage
import logging
import re
# Controller (External data)-> Service (Logic) -> Repository (sql queries)

logger = logging.getLogger(__name__)


ticket_name_pattern = re.compile(r"Ticket #(\d+) \(.+\)")

class Ticket(object):

    ticket_cache = {}
    open_tickets = {}

    def __init__(self, storage:Storage, client:AsyncClient, ticket_id:int=None, user_id:str=None, ticket_name:str=None, ticket_room_id:str=None):
        # Setup Storage bindings
        self.storage = storage
        self.client = client
        self.ticketRep:TicketRepository = self.storage.repositories.ticketRep
        self.userRep: UserRepository = self.storage.repositories.userRep

        # PK
        self.id = None

        # Find existing ticket if provided with ticket room id
        if ticket_id:
            # Check if Ticket exists with id
            exists = self.ticketRep.get_ticket_count(ticket_id) == 1
            if not exists:
                raise IndexError(f"Ticket with index {ticket_id} not found")
            else:
                self.id = ticket_id

        # If Ticket not found
        if not self.id:
            # If provided with user_id - create new ticket
            if user_id:
                self.user_id = user_id

                # Validate ticket/room name
                if not ticket_name:
                    # TODO: Use a default value from config
                    self.ticket_name = "General"
                else:
                    self.ticket_name = ticket_name

                self.id = self.ticketRep.create_ticket(user_id, ticket_room_id, self.ticket_name)
                self.status = TicketStatus.OPEN

            else:
                raise ValueError(f"ID of existing ticket not found and user_id/ticket_room_id not specified for new Ticket")
        else:
            # Fetch existing fields of Ticket
            fields = self.ticketRep.get_all_fields(self.id)

            self.id =               fields['id']
            self.user_id =          fields['user_id']
            self.ticket_room_id =   fields['ticket_room_id']
            self.status =           fields['status']
            self.ticket_name =      fields['ticket_name']

    @staticmethod
    def fetch_ticket_by_id(store, client, ticket_id:int):
        try:
            # Try to find a ticket by id
            ticket = Ticket(store, client, ticket_id=ticket_id)
        except IndexError as index_error:
            logger.debug(f"{index_error.args[0]}")
            return None
        return ticket

    @staticmethod
    def find_room_ticket_id(room:MatrixRoom):
        match = None
        if room.name:
            match = ticket_name_pattern.match(room.name)

        ticket_id = None
        if match:
            ticket_id = match[1]  # Get the id from regex group

        if ticket_id and ticket_id.isnumeric():
            return int(ticket_id)

    @staticmethod
    async def find_ticket_of_room(store, client, room:MatrixRoom):
        is_open_ticket_room = False
        ticket = None

        ticket_id = Ticket.find_room_ticket_id(room)
        if not ticket_id:
            return None

        should_add_to_cache = False
        if ticket_id in Ticket.open_tickets: # Check cache
            ticket = Ticket.open_tickets[ticket_id]
            should_add_to_cache = True
        else:
            try:
                ticket = Ticket(store, client, ticket_id=ticket_id)
            except Response as response:
                error_message = response if type(response == str) else getattr(response, "message",
                                                                               "Unknown error")
                await send_text_to_room(
                    client, room.room_id,
                    f"Failed to fetch Ticket of room with ticket id #{ticket_id}!  Error: {error_message}",
                )
                return None

        if ticket.ticket_room_id == room.room_id:
            if should_add_to_cache and ticket.status != TicketStatus.CLOSED:
                Ticket.open_tickets[ticket_id] = ticket
            return ticket
        else:
            logger.warning(
                f"Room {room.room_id} does not match Ticket #{ticket.id} room id {ticket.ticket_room_id}")

            return None

    async def create_ticket_room(self):
        # Request a Ticket reply room to be created.
        response = await create_room(self.client, f"Ticket #{self.id} ({self.ticket_name})")

        if isinstance(response, RoomCreateResponse):
            logger.debug(f"Created a Ticket room {response.room_id} successfully for ticket id {self.id}")
            self.ticket_room_id = response.room_id
            self.ticketRep.set_ticket_room_id(self.id, self.ticket_room_id)
            return response.room_id
        else:
            logger.debug(f"failed to create a room for ticket id {self.id}")
            raise Exception(response)

    async def invite_to_ticket_room(self, user_id:str):
        # Invite staff to the Ticket room
        logger.debug(f"Inviting user {user_id} to ticket room f{self.ticket_room_id}")
        response = await invite_to_room(self.client, user_id, self.ticket_room_id)

        if isinstance(response, RoomInviteResponse):
            logger.debug(f"Invited user to Ticket room successfully")
        else:
            logger.debug(f"failed to invite user to room:{response}")
            raise Exception(response)

    async def claim_ticket(self, staff_id:str):
        # Claim the ticket and be invited to the Ticket room

        staff = self.ticketRep.get_assigned_staff(self.id)

        if staff_id in [s['user_id'] for s in staff]:
            logger.debug(f"{staff_id} already assigned to this Ticket")
            return

        # Assign staff member to the ticket
        self.ticketRep.assign_staff_to_ticket(self.id, staff_id)

    async def close_ticket(self, staff_id:str):
        # Close the ticket the room contains by changing status to CLOSED
        self.ticketRep.set_ticket_status(self.id, TicketStatus.CLOSED.value)

        # Inform about closed room
        logger.debug(f"Staff {staff_id} closed ticket {self.id}")
        await send_text_to_room(
            self.client, self.ticket_room_id,
            f"Staff {staff_id} closed ticket {self.id}",
        )

    async def reopen_ticket(self, staff_id:str):
        # Reopen the ticket the room contains by changing status to OPEN
        self.ticketRep.set_ticket_status(self.id, TicketStatus.OPEN.value)

        # Inform about closed room
        logger.debug(f"Staff {staff_id} reopened ticket {self.id}")
        await send_text_to_room(
            self.client, self.ticket_room_id,
            f"Staff {staff_id} reopened ticket {self.id}",
        )

    def find_user_current_ticket_id(self):
        return self.userRep.get_user_current_ticket_id(self.user_id)
