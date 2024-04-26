import logging
import unittest
import sys
from unittest.mock import Mock, patch

import nio

from support_bot.callbacks import Callbacks
from support_bot.message_responses import TextMessage
from support_bot.storage import Storage

from tests.utils import make_awaitable, run_coroutine


class MessageResponsesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        # Setup Debug level logging
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stream_handler)
        
        self.maxDiff = None
        
        # Create a Callbacks object and give it some Mock'd objects to use
        self.fake_client = Mock(spec=nio.AsyncClient)
        self.fake_client.user = "@fake_user:example.com"
        self.fake_client.rooms = {}
        self.fake_client.access_token ="syt_fake_access_token"

        self.fake_storage = Mock(spec=Storage)
        self.fake_storage.repositories = Mock()

        self.fake_config = Mock()
        self.fake_config.management_room_id = "!fake_management_room_id:example.com"

        self.fake_client.callbacks = Callbacks(
            self.fake_client, self.fake_storage, self.fake_config
        )
                

        self.fake_message_room = Mock(spec=nio.MatrixRoom)
        self.fake_message_room.room_id = "fake_message_room_id:example.com"
        
        self.fake_event = Mock(spec=nio.RoomMessage)
        self.fake_event.room_id = self.fake_message_room.room_id
        
        self.fake_message_content = "Some fake message content source"
        
        # Setup a fake text message we received in a fake room with some message content
        self.text_message = TextMessage(
            self.fake_client,
            self.fake_storage,
            self.fake_config,
            self.fake_message_room,
            self.fake_event,
            self.fake_message_content
        )
        
    @patch('support_bot.chat_functions.send_text_to_room')
    def test_send_message_to_room(self, send_text_to_room):
        """Tests the send_message_to_room method"""
        # Tests that the bot successfully sends a text message to the specified room

        send_text_to_room.return_value = Mock(spec=nio.RoomSendResponse)
        
        # Create a fake room and invite event to call the 'invite' callback with
        fake_room = Mock(spec=nio.MatrixRoom)
        fake_room_id = "!abcdefg:example.com"
        fake_room.room_id = fake_room_id

        fake_text = "Some fake message content that has been filtered by parent methods."

        #fake_invite_event = Mock(spec=nio.InviteMemberEvent)
        #fake_invite_event.sender = "@some_other_fake_user:example.com"
        #fake_invite_event.source = {
        #    "event_id": "$4vk68QCqjeVOcz7X20OwUJe6IidTcl5O3f8EydVTWSU"
        #}

        # Pretend that sending a message to a room is always successful
        fake_room_send_response_success = Mock(spec=nio.RoomSendResponse)
        self.fake_client.room_send.return_value = make_awaitable(fake_room_send_response_success)

        # Pretend that we received are sending the message to a room
        run_coroutine(self.text_message.send_message_to_room(fake_text, fake_room.room_id))
        expected_task = (
            self.fake_client.callbacks._message,
            fake_room_id,
            self.fake_event.room_id,
            self.fake_event
        )
        expected_callback_dict = {
            fake_room.room_id : [expected_task]
        }

        self.assertDictEqual(self.fake_client.callbacks.rooms_pending, expected_callback_dict)
        # Check that we attempted to send the message to the designated room
        #send_text_to_room.assert_called_once_with(
        #    self.fake_client,
        #    fake_room.room_id,
        #    fake_text,
        #    )
        
    #def test_


if __name__ == "__main__":
    unittest.main()