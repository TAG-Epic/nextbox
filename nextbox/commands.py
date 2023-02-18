from __future__ import annotations

from .command_handler import BaseCommand
import typing
from discord_typings import MessageCreateData
from os import environ

if typing.TYPE_CHECKING:
    from . import ControlBot

BOT_OWNER_ID = environ["BOT_OWNER_ID"]

class CapacityCommand(BaseCommand):
    def __init__(self) -> None:
        super().__init__("capacity")

    async def run(self, control_bot: ControlBot, message: MessageCreateData, arguments: list[typing.Any]):
        del arguments

        output = []
        total_capacity = 0
        for worker_id, worker in enumerate(control_bot.workers):
            output.append(f"**{worker_id}:** {worker.capacity}")
            total_capacity += worker.capacity

        output.append(f"**__Total__:** {total_capacity}")
        formatted_output = "\n".join(output)

        await control_bot.http_client.create_message(control_bot.authentication, message["channel_id"], content=formatted_output)

class CleanupCommand(BaseCommand):
    def __init__(self):
        super().__init__("cleanup")

    async def run(self, control_bot: ControlBot, message: MessageCreateData, arguments: list[typing.Any]):
        del arguments

        for bot in control_bot.workers:
            await bot.cleanup_guilds(force=True)

        await control_bot.http_client.create_message(control_bot.authentication, message["channel_id"], content="Cleaned up excess guilds")

class CreateCommand(BaseCommand):
    def __init__(self):
        super().__init__("create")

    async def run(self, control_bot: ControlBot, message: MessageCreateData, arguments: list[typing.Any]):
        del arguments

        for worker in control_bot.workers:
            if worker.capacity == 0:
                continue
            break
        else:
            await control_bot.http_client.create_message(control_bot.authentication, message["channel_id"], content="The bot is currently full. Sorry!")
            return
        invite = await worker.create_guild()
        await control_bot.http_client.create_message(control_bot.authentication, message["channel_id"], content=f"Created: {invite}")
        
