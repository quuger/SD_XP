import threading
import time
import unittest
from concurrent import futures
from unittest.mock import Mock

import grpc

from app.grpc_client import GrpcClient
from app.grpc_server import ChatServer
from app.proto import chat_pb2, chat_pb2_grpc


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


class TestGrpcClient(unittest.TestCase):
    """Test cases for the GrpcClient class"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        self.server = ChatServer()
        self.port = 50052
        self.grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        chat_pb2_grpc.add_ChatServerServicer_to_server(self.server, self.grpc_server)
        self.grpc_server.add_insecure_port(f"[::]:{self.port}")
        self.grpc_server.start()

        self.username = "test_client"
        self.callback = Mock()

    def tearDown(self):
        """Clean up after each test method"""
        self.grpc_server.stop(grace=1)

    def test_client_initialization(self):
        """Test client initialization"""
        client = GrpcClient("localhost", self.port, self.username, self.callback)
        self.assertEqual(client.username, self.username)
        self.assertEqual(client.callback, self.callback)
        self.assertIsNotNone(client.connection)
        client.close()

    def test_send_message(self):
        """Test sending a message from client"""
        client = GrpcClient("localhost", self.port, self.username, self.callback)
        client.send_message("Hello, World!")
        time.sleep(0.1)
        self.assertEqual(len(self.server.chats), 1)
        self.assertEqual(self.server.chats[0].name, self.username)
        self.assertEqual(self.server.chats[0].text, "Hello, World!")
        self.assertIsNotNone(self.server.chats[0].timestamp)
        client.close()

    def test_send_empty_message(self):
        """Test sending empty message should be ignored"""
        client = GrpcClient("localhost", self.port, self.username, self.callback)

        client.send_message("")
        time.sleep(0.1)

        self.assertEqual(len(self.server.chats), 0)
        client.close()


if __name__ == "__main__":
    unittest.main()
