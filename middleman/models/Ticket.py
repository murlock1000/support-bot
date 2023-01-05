from middleman.storage import Storage

# Controller (External data)-> Service (Logic) -> Repository (sql queries)


class Ticket(object):
    def __init__(self, storage:Storage, user_id:str, user_room_id:str):
        # Setup Storage bindings
        self.storage = storage
        self.ticketRep = self.storage.repositories.ticketRep
        
        self.user_id = user_id
        self.user_room_id = user_room_id
        
        # Find existing ticket
        self.id = self.ticketRep.get_ticket_id(self.user_id, self.user_room_id)
        
        # Create Ticket entry if not found in DB
        if not self.id:      
            self.id = self.ticketRep.create_ticket(user_id, user_room_id)