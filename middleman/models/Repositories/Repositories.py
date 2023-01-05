from middleman.models.Repositories.StaffRepository import StaffRepository
from middleman.models.Repositories.TicketRepository import TicketRepository
from middleman.models.Repositories.UserRepository import UserRepository
from middleman.storage import Storage

class Repositories(object):
    def __init__(self, storage:Storage):
        self.storage = storage
        
        # Initialise global Repositories
        self.ticketRep = TicketRepository(self.storage)
        self.staffRep = StaffRepository(self.storage)
        self.userRep = UserRepository(self.storage)