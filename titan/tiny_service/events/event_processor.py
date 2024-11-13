from titan.tiny_service.events.event import Event


class EventProcessorException(Exception):
    pass

class EventProcessor:
    def process_event(self, event):
        raise NotImplementedError


class AsyncEventProcessor(EventProcessor):
    async def process_event(self, event):
        raise NotImplementedError