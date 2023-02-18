import asyncio
from nextcore.gateway import ShardManager
from nextcore.http import BotAuthentication, HTTPClient
from os import environ
from .worker import WorkerBot
import tre
import logging
from .command_handler import CommandHandler
from .commands import CapacityCommand, CleanupCommand, CreateCommand, HelpCommand

global_logger = logging.getLogger()
global_logger.setLevel(logging.DEBUG)
tre.setup(global_logger)

logger = logging.getLogger("nextbox")

CONTROL_TOKEN = environ["CONTROL_TOKEN"]
WORKER_TOKENS = environ["WORKER_TOKENS"].split(" ")

class ControlBot:
    def __init__(self) -> None:
        self.authentication = BotAuthentication(CONTROL_TOKEN)
        self.http_client = HTTPClient()
        self.shard_manager = ShardManager(self.authentication, 33280, self.http_client)
        self.command_handler: CommandHandler = CommandHandler("!", self)
        self.workers: list[WorkerBot] = []

    async def run(self):
        await self.http_client.setup()
        await self.shard_manager.connect()

        await self.start_workers()

        # Event listeners
        self.shard_manager.event_dispatcher.add_listener(self.command_handler.on_message, "MESSAGE_CREATE")

        # Commands
        self.command_handler.register(CapacityCommand())
        self.command_handler.register(CleanupCommand())
        self.command_handler.register(CreateCommand())
        self.command_handler.register(HelpCommand())
        
        error = await self.shard_manager.dispatcher.wait_for(lambda: True, "critical")
        logging.critical(error[0])
        await self.close()

    async def start_workers(self):
        for worker_token in WORKER_TOKENS:
            auth = BotAuthentication(worker_token)
            worker = WorkerBot(auth, self.http_client)
            await worker.connect()
            self.workers.append(worker)

    async def close(self):
        for worker in self.workers:
            await worker.close()
        
        await self.shard_manager.close()
        await self.http_client.close()


control_bot = ControlBot()

asyncio.run(control_bot.run())
