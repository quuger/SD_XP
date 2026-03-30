import argparse
import asyncio


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--name", required=True)
    parser.add_argument("--peer", help="host:port")

    args = parser.parse_args()

    grpc_client = GrpcClient(args.peer)

    controller = ChatController(args.name, grpc_client)
    cli = ChatCLI(controller)

    await controller.start()
    await cli.start()


if __name__ == "__main__":
    asyncio.run(main())
