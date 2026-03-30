import threading
import time
import unittest
from unittest.mock import Mock

from app.grpc_server import ChatServer
from app.proto import chat_pb2


class TestChatServer(unittest.TestCase):
    """Test cases for the ChatServer class"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        self.server = ChatServer()
        # Create a mock context for testing
        self.mock_context = Mock()
        self.mock_context.is_active.return_value = True

    def test_init(self):
        """Test server initialization"""
        self.assertEqual(self.server.chats, [])

    def test_send_multiple_messages(self):
        """Test sending multiple messages"""
        messages = [
            chat_pb2.ChatMessage(name="user1", text="msg1", timestamp=1),
            chat_pb2.ChatMessage(name="user2", text="msg2", timestamp=2),
            chat_pb2.ChatMessage(name="user3", text="msg3", timestamp=3),
        ]

        for msg in messages:
            self.server.SendMessage(msg, self.mock_context)

        self.assertEqual(len(self.server.chats), 3)
        for i, msg in enumerate(messages):
            self.assertEqual(self.server.chats[i].name, msg.name)
            self.assertEqual(self.server.chats[i].text, msg.text)

    def test_chat_stream_with_messages(self):
        """Test ChatStream with existing messages"""
        messages = [
            chat_pb2.ChatMessage(name="user1", text="msg1", timestamp=1),
            chat_pb2.ChatMessage(name="user2", text="msg2", timestamp=2),
        ]

        for msg in messages:
            self.server.SendMessage(msg, self.mock_context)

        stream = self.server.ChatStream(chat_pb2.Empty(), self.mock_context)

        for i, msg in enumerate(stream):
            self.assertEqual(messages[i].name, msg.name)
            self.assertEqual(messages[i].text, msg.text)
            if i + 1 == len(messages):
                break

    def test_chat_stream_with_new_messages(self):
        """Test ChatStream yields new messages as they arrive"""
        stream = self.server.ChatStream(iter([]), self.mock_context)
        results = []

        def collect_messages():
            for msg in stream:
                results.append(msg)
                if len(results) == 2:
                    break

        thread = threading.Thread(target=collect_messages)
        thread.daemon = True
        thread.start()

        time.sleep(0.1)
        msg1 = chat_pb2.ChatMessage(name="user1", text="msg1", timestamp=1)
        msg2 = chat_pb2.ChatMessage(name="user2", text="msg2", timestamp=2)

        self.server.SendMessage(msg1, self.mock_context)
        time.sleep(0.1)
        self.server.SendMessage(msg2, self.mock_context)

        time.sleep(0.1)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].text, "msg1")
        self.assertEqual(results[1].text, "msg2")

    def test_send_message_with_empty_text(self):
        """Test sending message with empty text"""
        request = chat_pb2.ChatMessage(name="test_user", text="", timestamp=1234567890)

        response = self.server.SendMessage(request, self.mock_context)

        self.assertEqual(len(self.server.chats), 1)
        self.assertEqual(self.server.chats[0].text, "")
        self.assertIsInstance(response, chat_pb2.Empty)

    def test_send_message_with_long_text(self):
        """Test sending message with very long text"""
        long_text = "a" * 10000
        request = chat_pb2.ChatMessage(
            name="test_user", text=long_text, timestamp=1234567890
        )

        self.server.SendMessage(request, self.mock_context)
        self.assertEqual(len(self.server.chats), 1)
        self.assertEqual(self.server.chats[0].text, long_text)


if __name__ == "__main__":
    unittest.main()
