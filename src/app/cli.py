import asyncio
import sys


class ChatCLI:
    def __init__(self, controller):
        self.controller = controller
        self.controller.on_message_callback = self.display_message

    async def start(self):
        print("=== P2P gRPC Chat ===")
        print("Введите сообщение:\n")

        await asyncio.gather(
            self._input_loop(),
        )

    async def _input_loop(self):
        loop = asyncio.get_event_loop()

        while True:
            text = await loop.run_in_executor(None, sys.stdin.readline)
            text = text.rstrip("\n")

            if not text:
                continue

            self._clear_last_line()

            await self.controller.send_message(text)

    def _clear_last_line(self):
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[K")
        sys.stdout.flush()

    async def display_message(self, msg):
        time_str = msg["timestamp"].strftime("%H:%M:%S")

        print(f"[{time_str}] {msg['name']}: {msg['text']}")
