from copilot import CopilotClient, PermissionHandler

client = CopilotClient()
await client.start()

session = await client.create_session(on_permission_request=PermissionHandler.approve_all, model="gpt-4.1")
response = await session.send_and_wait({"prompt": "Hello!"})
print(response.data.content)

await client.stop()