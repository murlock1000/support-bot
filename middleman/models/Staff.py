from middleman.models.Repositories.StaffRepository import StaffRepository
from middleman.storage import Storage

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class Staff(object):
    def __init__(self, storage:Storage, user_id:str, create_new:bool = False):
        # Setup Storage bindings
        self.storage = storage
        self.staffRep:StaffRepository = self.storage.repositories.staffRep

        # Find existing staff if provided with staff user id
        if create_new:
            # Create Staff entry if not found in DB
            if user_id:
                self.user_id = self.staffRep.create_staff(user_id)
        else:
            # Check if staff exists with id
            exists = self.staffRep.get_staff_count(user_id) == 1
            if not exists:
                raise IndexError(f"Staff with user id {user_id} not found")
            else:
                self.user_id = user_id