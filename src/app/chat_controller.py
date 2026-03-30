import asyncio
from datetime import datetime


class ChatController:
    def __init__(self, username: str, grpc_client):
        self.username = username
        self.grpc_client = grpc_client
        self.on_message_callback = None

    async def start(self):
        asyncio.create_task(self._listen_stream())

    async def _listen_stream(self):
        async for msg in self.grpc_client.chat_stream():
            await self._handle_incoming_message(msg)

    async def send_message(self, text: str):
        timestamp = int(datetime.utcnow().timestamp() * 1000)

        msg = {"name": self.username, "text": text, "timestamp": timestamp}

        await self.grpc_client.send_message(msg)

    async def _handle_incoming_message(self, msg):
        message = {
            "name": msg.name,
            "text": msg.text,
            "timestamp": datetime.fromtimestamp(msg.timestamp / 1000),
        }

        if self.on_message_callback:
            await self.on_message_callback(message)
