"""
End-to-End tests for P2P gRPC Chat application.

Tests cover:
1. Server startup and shutdown
2. Client connection and message sending
3. Message streaming between multiple clients
4. Full integration scenarios
"""

import os
import sys
import threading
import time
from concurrent import futures
from datetime import datetime

import grpc
import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from app.chat_controller import ChatController
from app.grpc_client import GrpcClient
from app.grpc_server import ChatServer
from app.proto import chat_pb2, chat_pb2_grpc


class TestChatServerE2E:
    """End-to-end tests for the gRPC chat server."""

    @pytest.fixture
    def server_port(self):
        """Get a free port for testing."""
        import socket

        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    @pytest.fixture
    def running_server(self, server_port):
        """Start and stop a gRPC server for each test."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        chat_pb2_grpc.add_ChatServerServicer_to_server(ChatServer(), server)
        server.add_insecure_port(f"[::]:{server_port}")
        server.start()

        yield server_port

        server.stop(grace=0)

    def test_server_starts_and_accepts_connections(self, running_server):
        """Test that server starts and accepts gRPC connections."""
        port = running_server

        channel = grpc.insecure_channel(f"localhost:{port}")
        stub = chat_pb2_grpc.ChatServerStub(channel)

        response = stub.SendMessage(
            chat_pb2.ChatMessage(
                name="test_user", text="Hello", timestamp=time.time_ns()
            )
        )

        assert isinstance(response, chat_pb2.Empty)
        channel.close()

    def test_server_broadcasts_messages_to_stream(self, running_server):
        """Test that messages sent to server are available in stream."""
        port = running_server

        channel = grpc.insecure_channel(f"localhost:{port}")
        stub = chat_pb2_grpc.ChatServerStub(channel)

        sent_messages = []

        def send_messages():
            for i in range(3):
                msg = chat_pb2.ChatMessage(
                    name=f"user_{i}", text=f"Message {i}", timestamp=time.time_ns()
                )
                stub.SendMessage(msg)
                sent_messages.append(msg)
                time.sleep(0.1)

        send_thread = threading.Thread(target=send_messages)
        send_thread.start()

        received_messages = []
        stream = stub.ChatStream(chat_pb2.Empty())

        # Read messages with timeout using iterator
        deadline = time.time() + 2
        while len(received_messages) < 3 and time.time() < deadline:
            try:
                msg = next(stream)
                received_messages.append(msg)
            except grpc.RpcError:
                break
            except StopIteration:
                break

        send_thread.join()

        assert len(received_messages) == 3
        for i, msg in enumerate(received_messages):
            assert msg.name == f"user_{i}"
            assert msg.text == f"Message {i}"

        channel.close()


class TestGrpcClientE2E:
    """End-to-end tests for the gRPC client."""

    @pytest.fixture
    def server_port(self):
        """Get a free port for testing."""
        import socket

        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    @pytest.fixture
    def running_server(self, server_port):
        """Start a gRPC server for client tests."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        chat_pb2_grpc.add_ChatServerServicer_to_server(ChatServer(), server)
        server.add_insecure_port(f"[::]:{server_port}")
        server.start()

        yield server_port

        server.stop(grace=0)

    def test_client_connects_and_sends_message(self, running_server):
        """Test that client can connect and send messages."""
        port = running_server
        received_messages = []

        def on_message(msg):
            received_messages.append(msg)

        client = GrpcClient(
            host="localhost", port=port, username="test_user", callback=on_message
        )

        time.sleep(0.2)

        client.send_message("Hello, World!")

        time.sleep(0.5)

        assert len(received_messages) >= 1
        assert received_messages[0].name == "test_user"
        assert received_messages[0].text == "Hello, World!"

    def test_client_receives_broadcast_messages(self, running_server):
        """Test that client receives messages from other users."""
        port = running_server
        received_messages = []

        def on_message(msg):
            received_messages.append(msg)

        client = GrpcClient(
            host="localhost", port=port, username="listener_user", callback=on_message
        )

        time.sleep(0.3)

        channel = grpc.insecure_channel(f"localhost:{port}")
        stub = chat_pb2_grpc.ChatServerStub(channel)

        stub.SendMessage(
            chat_pb2.ChatMessage(
                name="other_user", text="Test message", timestamp=time.time_ns()
            )
        )

        time.sleep(0.5)

        assert len(received_messages) >= 1
        assert received_messages[0].name == "other_user"
        assert received_messages[0].text == "Test message"

        channel.close()


class TestChatControllerE2E:
    """End-to-end tests for the ChatController."""

    @pytest.fixture
    def server_port(self):
        """Get a free port for testing."""
        import socket

        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    @pytest.fixture
    def running_server(self, server_port):
        """Start a gRPC server for controller tests."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        chat_pb2_grpc.add_ChatServerServicer_to_server(ChatServer(), server)
        server.add_insecure_port(f"[::]:{server_port}")
        server.start()

        yield server_port

        server.stop(grace=0)

    def test_controller_sends_message(self, running_server):
        """Test that controller sends messages through client."""
        port = running_server
        received_messages = []

        def on_message(msg):
            received_messages.append(msg)

        grpc_client = GrpcClient(
            host="localhost", port=port, username="controller_user", callback=on_message
        )

        controller = ChatController("controller_user", grpc_client)

        time.sleep(0.2)
        controller.send_message("Message from controller")
        time.sleep(0.5)

        assert len(received_messages) >= 1
        assert received_messages[0].text == "Message from controller"

    def test_controller_handles_incoming_message(self, running_server):
        """Test that controller properly handles incoming messages."""
        port = running_server
        handled_messages = []

        def on_message(msg):
            handled_messages.append(msg)

        grpc_client = GrpcClient(
            host="localhost", port=port, username="test_user", callback=lambda x: None
        )

        controller = ChatController("test_user", grpc_client)
        controller.on_message_callback = on_message

        mock_msg = chat_pb2.ChatMessage(
            name="sender", text="Test text", timestamp=time.time_ns()
        )

        controller.handle_incoming_message(mock_msg)

        assert len(handled_messages) == 1
        assert handled_messages[0]["name"] == "sender"
        assert handled_messages[0]["text"] == "Test text"
        assert isinstance(handled_messages[0]["timestamp"], datetime)


class TestMultiClientIntegration:
    """Integration tests with multiple clients."""

    @pytest.fixture
    def server_port(self):
        """Get a free port for testing."""
        import socket

        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    @pytest.fixture
    def running_server(self, server_port):
        """Start a gRPC server for integration tests."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        chat_pb2_grpc.add_ChatServerServicer_to_server(ChatServer(), server)
        server.add_insecure_port(f"[::]:{server_port}")
        server.start()

        yield server_port

        server.stop(grace=0)

    def test_multiple_clients_exchange_messages(self, running_server):
        """Test that multiple clients can exchange messages."""
        port = running_server

        client1_messages = []
        client2_messages = []

        def on_message_1(msg):
            client1_messages.append(msg)

        def on_message_2(msg):
            client2_messages.append(msg)

        client1 = GrpcClient(
            host="localhost", port=port, username="client_1", callback=on_message_1
        )

        time.sleep(0.2)

        client2 = GrpcClient(
            host="localhost", port=port, username="client_2", callback=on_message_2
        )

        time.sleep(0.3)

        client1.send_message("Hello from client 1")
        time.sleep(0.3)

        client2.send_message("Hello from client 2")
        time.sleep(0.3)

        client1.send_message("Another message from client 1")
        time.sleep(0.3)

        assert len(client1_messages) >= 3
        assert len(client2_messages) >= 3

        client1_texts = [m.text for m in client1_messages]
        client2_texts = [m.text for m in client2_messages]

        assert "Hello from client 1" in client1_texts
        assert "Hello from client 2" in client1_texts
        assert "Another message from client 1" in client1_texts

        assert "Hello from client 1" in client2_texts
        assert "Hello from client 2" in client2_texts
        assert "Another message from client 1" in client2_texts

    def test_full_chat_scenario(self, running_server):
        """Test a complete chat scenario with multiple participants."""
        port = running_server

        chat_history = {"alice": [], "bob": [], "charlie": []}

        def make_callback(name):
            def callback(msg):
                chat_history[name].append(msg)

            return callback

        clients = {}
        for name in ["alice", "bob", "charlie"]:
            clients[name] = GrpcClient(
                host="localhost", port=port, username=name, callback=make_callback(name)
            )
            time.sleep(0.1)

        time.sleep(0.3)

        clients["alice"].send_message("Hi everyone!")
        time.sleep(0.2)

        clients["bob"].send_message("Hello Alice!")
        time.sleep(0.2)

        clients["charlie"].send_message("Hey all!")
        time.sleep(0.2)

        clients["alice"].send_message("How is everyone?")
        time.sleep(0.3)

        for name in ["alice", "bob", "charlie"]:
            assert len(chat_history[name]) >= 4

            texts = [m.text for m in chat_history[name]]
            assert "Hi everyone!" in texts
            assert "Hello Alice!" in texts
            assert "Hey all!" in texts
            assert "How is everyone?" in texts


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def server_port(self):
        """Get a free port for testing."""
        import socket

        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    @pytest.fixture
    def running_server(self, server_port):
        """Start a gRPC server for edge case tests."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        chat_pb2_grpc.add_ChatServerServicer_to_server(ChatServer(), server)
        server.add_insecure_port(f"[::]:{server_port}")
        server.start()

        yield server_port

        server.stop(grace=0)

    def test_empty_message_handling(self, running_server):
        """Test handling of empty messages."""
        port = running_server
        received_messages = []

        def on_message(msg):
            received_messages.append(msg)

        client = GrpcClient(
            host="localhost", port=port, username="test_user", callback=on_message
        )

        time.sleep(0.2)

        client.send_message("")

        time.sleep(0.3)

        empty_messages = [m for m in received_messages if m.text == ""]
        assert len(empty_messages) == 0

    def test_long_message_handling(self, running_server):
        """Test handling of long messages."""
        port = running_server
        received_messages = []

        def on_message(msg):
            received_messages.append(msg)

        client = GrpcClient(
            host="localhost", port=port, username="test_user", callback=on_message
        )

        time.sleep(0.2)

        long_message = "A" * 10000
        client.send_message(long_message)

        time.sleep(0.3)

        assert len(received_messages) >= 1
        assert received_messages[0].text == long_message

    def test_special_characters_in_message(self, running_server):
        """Test handling of special characters in messages."""
        port = running_server
        received_messages = []

        def on_message(msg):
            received_messages.append(msg)

        client = GrpcClient(
            host="localhost", port=port, username="test_user", callback=on_message
        )

        time.sleep(0.2)

        special_message = "Hello! @#$%^&*()_+ 你好 🎉"
        client.send_message(special_message)

        time.sleep(0.3)

        assert len(received_messages) >= 1
        assert received_messages[0].text == special_message

    def test_rapid_message_sequence(self, running_server):
        """Test handling of rapid message sequences."""
        port = running_server
        received_messages = []

        def on_message(msg):
            received_messages.append(msg)

        client = GrpcClient(
            host="localhost", port=port, username="test_user", callback=on_message
        )

        time.sleep(0.2)

        for i in range(10):
            client.send_message(f"Rapid message {i}")

        time.sleep(1.0)

        assert len(received_messages) >= 10

        for i in range(10):
            assert f"Rapid message {i}" in [m.text for m in received_messages]
