from titan.tiny_service.events.event import Event
from titan.tiny_service.events.event_processor import EventProcessor

class EventToCommandTranslatorException(Exception):
    pass


class EventToCommandTranslator(EventProcessor):
    def translate_event_into_commands(self, event: Event):
        raise NotImplementedError