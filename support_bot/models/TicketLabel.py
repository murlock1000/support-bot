from support_bot.models.Repositories.TicketLabelsRepository import TicketLabelsRepository
from support_bot.storage import Storage

class TicketLabel(object):
    def __init__(self, storage:Storage, label_id:int):
        # Setup Storage bindings
        self.storage = storage
        self.ticketLabelsRep:TicketLabelsRepository = self.storage.repositories.ticketLabelsRep

        # Fetch existing fields of Ticket
        self.data = self.ticketLabelsRep.get_all_fields(label_id)

    @staticmethod
    def get_existing(storage:Storage, label_id:int):
        # Find existing ticket label
        exists = storage.repositories.ticketLabelsRep.get_label(label_id)
        if not exists:
            return None
        else:
            return TicketLabel(storage, label_id)

    @staticmethod
    def create_new(storage:Storage, name:str, hex_color: str, description: str = ""):
        # Create Support entry if not found in DB
        label_id = storage.repositories.ticketLabelsRep.create_label(name, description, hex_color)
        
        if label_id:
            ticketLabel = TicketLabel(storage, label_id)
            return ticketLabel
        else:
            return None

    def set_name(self, name:str):
        self.ticketLabelsRep.set_label_name(self.data.id, name)
        self.data.name = name
    
    def set_description(self, description:str):
        self.ticketLabelsRep.set_label_name(self.data.id, description)
        self.data.description = description
        
    def set_color(self, color:str):
        self.ticketLabelsRep.set_label_name(self.data.id, color)
        self.data.color = color
        
    def delete(self):
        self.ticketLabelsRep.delete_label(self.data.id)
        self.data = None