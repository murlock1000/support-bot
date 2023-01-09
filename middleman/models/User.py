from middleman.models.Repositories.UserRepository import UserRepository
from middleman.storage import Storage

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class User(object):
    def __init__(self, storage:Storage, user_id:str):        
        # Setup storage bindings
        self.storage = storage
        self.userRep:UserRepository = self.storage.repositories.userRep
        
        # Find existing User
        self.user_id = self.userRep.get_user(user_id)
        
        # Create User entry if not found in DB
        if not self.user_id:
            self.user_id = self.userRep.create_user(user_id)
        else:
            self.room_id = self.userRep.get_user_room(user_id)

    def update_communications_room(self, room_id: str):
        if room_id:
            self.userRep.set_user_room(self.user_id, room_id)
            self.room_id = room_id
        else:
            raise ValueError("Invalid room id")