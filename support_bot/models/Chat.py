from datetime import datetime
from typing import List
from nio import AsyncClient, RoomCreateResponse, RoomInviteResponse, MatrixRoom, Response, RoomCreateError

from support_bot.chat_functions import invite_to_room, create_room, send_text_to_room
from support_bot.models.Repositories.ChatRepository import ChatRepository, ChatStatus
from support_bot.models.Repositories.UserRepository import UserRepository
from support_bot.storage import Storage
import logging
import re
# Controller (External data)-> Service (Logic) -> Repository (sql queries)

logger = logging.getLogger(__name__)

chat_room_name_pattern = re.compile(r"^Chat:")

class Chat(object):

    chat_cache = {}

    def __init__(self, storage:Storage, chat_room_id:str):
        # Setup Storage bindings
        self.storage = storage
        self.chatRep:ChatRepository = self.storage.repositories.chatRep
        self.userRep: UserRepository = self.storage.repositories.userRep

        # Fetch existing fields of Ticket
        fields = self.chatRep.get_all_fields(chat_room_id)

        self.chat_room_id =     fields['chat_room_id']
        self.user_id =          fields['user_id']
        self.status =           ChatStatus(fields['status'])
        self.created_at =       fields['created_at']
        self.closed_at =        fields['closed_at']

    @staticmethod
    def get_existing(storage: Storage, chat_room_id: str):
        # Check cache first
        chat = Chat.chat_cache.get(chat_room_id, None)
        if chat:
            return chat

        # Find existing Chat in Database
        exists = storage.repositories.chatRep.get_chat(chat_room_id)
        if exists:
            chat = Chat(storage, chat_room_id)
            # Add chat to cache
            Chat.chat_cache[chat_room_id] = chat
            return chat
        else:
            return None

    @staticmethod
    async def create_new(storage: Storage, client:AsyncClient, user_id:str):
        # Create chat room
        created_at = datetime.now()
        response = await Chat.create_chat_room(client, user_id)

        if isinstance(response, RoomCreateError):
            return response

        chat_room_id = response

        # Create Chat entry
        try:
            storage.repositories.chatRep.create_chat(user_id, chat_room_id, created_at)
        except Exception as e:
            return e

        chat = Chat(storage, chat_room_id)
        # Add chat to cache
        Chat.chat_cache[chat_room_id] = chat
        return chat

    @staticmethod
    def get_chat_room_id_from_room_id(store:Storage, room_id:str):
        return store.repositories.chatRep.get_chat(room_id)
    
    @staticmethod
    def find_chat_of_room(store, room:MatrixRoom):

        chat_room_id = room.room_id

        should_add_to_cache = False
        chat = Chat.chat_cache.get(chat_room_id, None)
        # Cache hit
        if chat:
            return chat

        # Cache miss
        chat = Chat.get_existing(store, chat_room_id)

        if chat:
            Chat.chat_cache[chat.chat_room_id] = chat
            return chat
        else:
            return None

    @staticmethod
    async def create_chat_room(client:AsyncClient, user_id:str, invite:List[str] = []):
        # Request a Chat room to be created.
        response = await create_room(client, f"Chat: {user_id})", invite)

        if isinstance(response, RoomCreateResponse):
            return response.room_id

        return response

    async def invite_to_chat_room(self, client:AsyncClient, user_id:str):
        # Invite staff to the Chat room
        response = await invite_to_room(client, user_id, self.chat_room_id)
        return response

    def claim_chat(self, staff_id:str):
        # Claim the chat for staff member

        staff = self.chatRep.get_assigned_staff(self.chat_room_id)

        # Check if staff not assigned to chat already
        if staff_id in [s['user_id'] for s in staff]:
            return

        # Assign staff member to the chat
        self.chatRep.assign_staff_to_chat(self.chat_room_id, staff_id)
        
    def claimfor_chat(self, support_id:str):
        # Claim the chat for support member

        support = self.chatRep.get_assigned_support(self.chat_room_id)

        # Check if support not assigned to ticket already
        if support_id in [s['user_id'] for s in support]:
            return

        # Assign support member to the ticket
        self.chatRep.assign_support_to_chat(self.chat_room_id, support_id)
        
    def get_assigned_support(self):
        support = self.chatRep.get_assigned_support(self.chat_room_id)

        return [s['user_id'] for s in support]
    
    def unassign_support(self, support_id:str):
        self.chatRep.remove_support_from_chat(self.chat_room_id, support_id)
        
    def unassign_staff(self, staff_id:str):
        self.chatRep.remove_staff_from_chat(self.chat_room_id, staff_id)
    
    def get_assigned_staff(self):
        staff = self.chatRep.get_assigned_staff(self.chat_room_id)

        return [s['user_id'] for s in staff]
        
    def _close_chat(self):
        self.chatRep.set_chat_closed_at(self.chat_room_id, datetime.now())
        
        # Remove from cache if closing chat
        if Chat.chat_cache.get(self.chat_room_id):
            Chat.chat_cache.pop(self.chat_room_id)
    
    def _open_chat(self):
        self.chatRep.set_chat_closed_at(self.chat_room_id, None)
        
        # Remove from cache if closing chat
        if Chat.chat_cache.get(self.chat_room_id):
            Chat.chat_cache.pop(self.chat_room_id)
            
    def set_status(self, status:ChatStatus):
        self.chatRep.set_chat_status(self.chat_room_id, status.value)
        self.status = status

        if status == ChatStatus.CLOSED:
            self._close_chat()
        elif status == ChatStatus.OPEN:
            self._open_chat()
        elif status == ChatStatus.DELETED:
            if Chat.chat_cache.get(self.chat_room_id):
                Chat.chat_cache.pop(self.chat_room_id)

    def find_user_current_chat_room_id(self):
        return self.userRep.get_user_current_chat_room_id(self.user_id)
