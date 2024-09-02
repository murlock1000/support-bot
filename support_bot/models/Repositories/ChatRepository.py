from support_bot.storage import Storage
from enum import Enum
from datetime import datetime

class ChatStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    DELETED = "deleted"

class ChatRepository(object):
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def create_chat(self, user_id: str, chat_room_id: str, created_at:datetime):
        self.storage._execute("""
            INSERT INTO Chats (user_id, chat_room_id, created_at) values (?, ?, ?);
        """, (user_id, chat_room_id, created_at,))

    def get_chat(self, chat_room_id: str):
        self.storage._execute("SELECT chat_room_id FROM Chats WHERE chat_room_id= ?;", (chat_room_id,))
        chat_room_id = self.storage.cursor.fetchone()
        if chat_room_id:
            return chat_room_id[0]
        return chat_room_id

    def assign_staff_to_chat(self, chat_room_id: str, staff_id: str):
        self.storage._execute("""
            insert into ChatsStaffRelation (chat_room_id, staff_id) values (?, ?);
        """, (chat_room_id, staff_id,))

    def get_assigned_staff(self, chat_room_id: str):
        self.storage._execute("""
            SELECT staff_id FROM ChatsStaffRelation WHERE chat_room_id = ?;
        """, (chat_room_id,))
        staff = self.storage.cursor.fetchall()
        return [
            {
                "user_id": row[0],
            } for row in staff
        ]

    def assign_support_to_chat(self, chat_room_id: int, support_id:str):
        self.storage._execute("""
            insert into ChatsSupportRelation (chat_room_id, support_id) values (?, ?);
        """, (chat_room_id, support_id,))

    def get_assigned_support(self, chat_room_id:int):
        self.storage._execute("""
            SELECT support_id FROM ChatsSupportRelation WHERE chat_room_id = ?;
        """, (chat_room_id,))
        support = self.storage.cursor.fetchall()
        return [
            {
                "user_id": row[0],
            } for row in support
        ]

    def remove_support_from_chat(self, chat_room_id: int, support_id:str):
        self.storage._execute("""
            DELETE FROM ChatsSupportRelation WHERE chat_room_id= ? AND support_id= ?
        """, (chat_room_id, support_id))
        
    def set_chat_status(self, chat_room_id:int, status:str):
        self.storage._execute("""
            UPDATE Chats SET status= ? WHERE chat_room_id=?
        """, (status, chat_room_id))
    
    def get_chat_status(self, chat_room_id: int):
        self.storage._execute("""
            SELECT status FROM Chats WHERE chat_room_id=?
        """, (chat_room_id,))
        
    def set_chat_closed_at(self, chat_room_id:int, closed_at:datetime):
        self.storage._execute("""
            UPDATE Chats SET closed_at= ? WHERE chat_room_id=?
        """, (closed_at, chat_room_id))
        
    def remove_staff_from_chat(self, chat_room_id: str, staff_id: str):
        self.storage._execute("""
            DELETE FROM ChatsStaffRelation WHERE chat_room_id= ? AND staff_id= ?
        """, (chat_room_id, staff_id))

    def get_all_fields(self, chat_room_id: str):
        self.storage._execute("""
            select chat_room_id, user_id, status, created_at, closed_at from Chats where chat_room_id = ?;
        """, (chat_room_id,))
        row = self.storage.cursor.fetchone()

        return {
            "chat_room_id": row[0],
            "user_id": row[1],
            "status": row[2],
            "created_at": row[3],
            "closed_at": row[4],
        }
        
    def get_open_chats(self):
        self.storage._execute("""
            SELECT chat_room_id, user_id FROM Chats WHERE status=?
        """, (ChatStatus.OPEN.value,))

        chats = self.storage.cursor.fetchall()
        return [
            {
                'chat_room_id':chat[0],
                'user_id': chat[1],
            } for chat in chats
        ]

    def get_open_chats_of_staff(self, staff_id:str):
        self.storage._execute("""
            SELECT chat_room_id, user_id FROM Chats t JOIN ChatsStaffRelation ts ON t.chat_room_id=ts.chat_room_id WHERE status=? AND staff_id=?
        """, (ChatStatus.OPEN.value, staff_id, ))

        chats = self.storage.cursor.fetchall()
        return [
            {
                'chat_room_id':chat[0],
                'user_id': chat[1],
            } for chat in chats
        ]