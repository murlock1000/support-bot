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
        id = self.storage.cursor.fetchone()[0]
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