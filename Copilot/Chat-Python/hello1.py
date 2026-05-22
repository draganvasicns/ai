import asyncio
from copilot import CopilotClient
from copilot.session import PermissionHandler

async def main():
    client = CopilotClient()
    await client.start()

    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        model="gpt-4.1"
    )
    response = await session.send_and_wait("Hello!")
    print(response.data.content)

    await client.stop()

if __name__ == "__main__":
    asyncio.run(main())