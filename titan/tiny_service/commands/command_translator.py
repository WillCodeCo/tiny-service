from titan.tiny_service.commands.command import Command
from titan.tiny_service.events.event import Event
from titan.tiny_service.events.event_processor import EventProcessor

class CommandTranslatorException(Exception):
    pass


class CommandTranslator(EventProcessor):
    def translate_command(self, command: Command):
        raise NotImplementedError

