from middleman.storage import Storage
from enum import Enum

class TicketStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    IN_PROGRESS = "in_progress"
    STUCK = "STUCK"

class TicketRepository(object):
    def __init__(self, storage:Storage) -> None:
        self.storage = storage
    
    def create_ticket(self, user_id:str, user_room_id: str):
        self.storage._execute("""
            insert into Tickets (user_room_id, user_id) values (?, ?);
        """, (user_room_id, user_id))
        return self.storage.cursor.lastrowid
        
    def get_ticket_id(self, user_id:str, user_room_id: str):
        self.storage._execute("SELECT id FROM Tickets WHERE user_id= ? AND user_room_id= ?;", (user_id, user_room_id,))
        id = self.storage.cursor.fetchone()
        return id
    
    def assign_staff_to_ticket(self, ticket_id: int, staff_id:str):
        self.storage._execute("""
            insert into TicketsStaffRelation (ticket_id, staff_id) values (?, ?);
        """, (ticket_id, staff_id))
    
    def get_assigned_staff(self, ticket_id:int):
        self._execute("""
            SELECT staff_id FROM TicketsStaffRelation WHERE ticket_id = ?;
        """, (ticket_id,))
        staff = self.cursor.fetchall()
        return [
            {
                "user_id": row[0],
            } for row in staff
        ]
    
    def remove_staff_from_ticket(self, ticket_id: int, staff_id:str):
        self.storage._execute("""
            DELETE FROM TicketsStaffRelation WHERE ticket_id= ? AND staff_id= ?
        """, (ticket_id, staff_id))
    
    def set_ticket_status(self, ticket_id:int, status:str):
        self.storage._execute("""
            UPDATE Tickets SET status= ? WHERE id=?
        """, (status, ticket_id))