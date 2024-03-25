from __future__ import annotations
from typing import List
from support_bot.models.Repositories.IncomingEventsRepository import IncomingEventsRepository
from support_bot.storage import Storage

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class IncomingEvent(object):
    def __init__(self, storage:Storage, user_id:str, room_id:str, event_id:str):
        # Setup Storage bindings
        self.storage = storage
        self.incomingEventsRep:IncomingEventsRepository = self.storage.repositories.incomingEventsRep
        
        self.user_id = user_id
        self.room_id = room_id
        self.event_id = event_id

    @staticmethod
    def get_incoming_events(storage:Storage, user_id:str) -> List[IncomingEvent]:
        # Fetch all incoming events from user that have not been sent to a ticket room
        result = storage.repositories.incomingEventsRep.get_incoming_events(user_id)
        incoming_events = []
        
        for row in result:
            event = IncomingEvent(storage, user_id, row['room_id'], row['event_id'])
            incoming_events.append(event)
            
        return incoming_events

    @staticmethod
    def delete_user_incoming_events(storage:Storage, user_id:str):
        storage.repositories.incomingEventsRep.delete_user_incoming_events(user_id)
        
    def store_incoming_event(self):
        # Store incoming event from user to be sent to a ticket room when created
        self.incomingEventsRep.put_incoming_event(self.user_id, self.room_id, self.event_id)
        
    