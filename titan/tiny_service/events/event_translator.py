from titan.tiny_service.events.event import Event
from titan.tiny_service.events.event_processor import EventProcessor

class EventTranslatorException(Exception):
    pass


class EventTranslator(EventProcessor):
    def translate_event(self, event: Event):
        raise NotImplementedError

