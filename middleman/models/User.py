from middleman.storage import Storage

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class User(object):
    def __init__(self, storage:Storage, user_id:str):        
        # Setup storage bindings
        self.storage = storage
        self.userRep = self.storage.repositories.userRep
        
        # Find existing User
        self.user_id = self.userRep.get_user(self.user_id)
        
        # Create User entry if not found in DB
        if not self.user_id:
            self.user_id = self.userRep.create_user(self.user_id)