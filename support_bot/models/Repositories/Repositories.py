from support_bot.models.Repositories.ChatRepository import ChatRepository
from support_bot.models.Repositories.EventPairsRepository import EventPairsRepository
from support_bot.models.Repositories.IncomingEventsRepository import IncomingEventsRepository
from support_bot.models.Repositories.StaffRepository import StaffRepository
from support_bot.models.Repositories.SupportRepository import SupportRepository
from support_bot.models.Repositories.TicketLabelsRepository import TicketLabelsRepository
from support_bot.models.Repositories.TicketRepository import TicketRepository
from support_bot.models.Repositories.UserRepository import UserRepository
from support_bot.storage import Storage

class Repositories(object):
    def __init__(self, storage:Storage):
        self.storage = storage
        
        # Initialise global Repositories
        self.ticketRep = TicketRepository(self.storage)
        self.staffRep = StaffRepository(self.storage)
        self.supportRep = SupportRepository(self.storage)
        self.userRep = UserRepository(self.storage)
        self.chatRep = ChatRepository(self.storage)
        self.incomingEventsRep = IncomingEventsRepository(self.storage)
        self.eventPairsRep = EventPairsRepository(self.storage)
        self.ticketLabelsRep = TicketLabelsRepository(self.storage)