from middleman.models.Repositories.StaffRepository import StaffRepository
from middleman.storage import Storage

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class Staff(object):
    def __init__(self, storage:Storage, user_id:str):
        # Setup Storage bindings
        self.storage = storage
        self.staffRep = self.storage.repositories.staffRep
          
        # Find existing staff
        self.user_id = self.staffRep.get_staff(self.user_id)
        
        # Create Staff entry if not found in DB
        if not self.user_id:
            self.user_id = self.staffRep.create_staff(self.user_id)