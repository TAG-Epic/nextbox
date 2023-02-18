from __future__ import annotations
import typing
from discord_typings import MessageCreateData

if typing.TYPE_CHECKING:
    from . import ControlBot

from nextcore.gateway import ShardManager

class BaseCommand:
    def __init__(self, name: str, *, description: str | None = None, arguments: list[BaseArgument] | None = None):
        self.name = name
        self.description = description
        self.arguments = arguments or []

    async def run(self, control_bot: ControlBot, message: MessageCreateData, arguments: list[typing.Any]):
        ...

class BaseArgument:
    def __repr__(self):
        return "impl-__repr__"
    def convert(self, control_bot: ControlBot, input: str) -> typing.Any:
        del input
        return NotImplementedError()

class CommandHandler:
    def __init__(self, prefix: str, control_bot: ControlBot) -> None:
        self.prefix = prefix
        self.control_bot = control_bot
        self.commands: dict[str, BaseCommand] = {}

    async def on_message(self, message_data: MessageCreateData):
        message_content = message_data["content"] or ""
        if not message_content.startswith(self.prefix):
            return
        arguments = message_content.removeprefix(self.prefix).split(" ")
        
        command_name = arguments.pop(0) # No need to keep the command

        command = self.commands.get(command_name)

        if command is None:
            return # Command not found

        if len(arguments) != len(command.arguments):
            return # Wrong number of arguments. TODO: Error handling?

        converted_arguments = [converter.convert(self.control_bot, argument) for converter, argument in zip(command.arguments, arguments)]

        await command.run(self.control_bot, message_data, converted_arguments)

    def register(self, command: BaseCommand):
        self.commands[command.name] = command
        
        
