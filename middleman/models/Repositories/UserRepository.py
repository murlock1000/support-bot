from typing import Union

from middleman.storage import Storage

class UserRepository(object):
    def __init__(self, storage:Storage) -> None:
        self.storage = storage
        
    def create_user(self, user_id:str):
        self.storage._execute("""
            insert into Users (user_id) values (?);
        """, (user_id,))
        return user_id
        
    def get_user(self, user_id:str):
        self.storage._execute("SELECT user_id FROM Users WHERE user_id= ?;", (user_id,))
        id = self.storage.cursor.fetchone()
        if id:
            return id[0]
        return id
    
    def delete_user(self, user_id:str):
        self.storage._execute("""
            DELETE FROM Users WHERE user_id= ?;
        """, (user_id,))

    def set_user_room(self, user_id:str, room_id:str):
        self.storage._execute("""
            UPDATE Users SET room_id= ? WHERE user_id=?
        """, (room_id, user_id))

    def get_user_room(self, user_id: str):
        self.storage._execute("""
            SELECT room_id FROM Users WHERE user_id=?
        """, (user_id,))
        room_id = self.storage.cursor.fetchone()
        if room_id:
            return room_id[0]
        return room_id

    def set_user_current_ticket_id(self, user_id:str, current_ticket_id:Union[int, None]):
        self.storage._execute("""
            UPDATE Users SET current_ticket_id= ? WHERE user_id=?
        """, (current_ticket_id, user_id))

    def get_user_current_ticket_id(self, user_id: str):
        self.storage._execute("""
            SELECT current_ticket_id FROM Users WHERE user_id=?
        """, (user_id,))
        current_ticket_id = self.storage.cursor.fetchone()
        if current_ticket_id:
            return current_ticket_id[0]
        return current_ticket_id

    def get_all_fields(self, user_id:str):
        self.storage._execute("""
            select user_id, room_id, current_ticket_id from Users where user_id = ?;
        """, (user_id,))
        row = self.storage.cursor.fetchone()

        return {
                "user_id": row[0],
                "room_id": row[1],
                "current_ticket_id": row[2],
            }