from titan.tiny_service.events.event import Event
from titan.tiny_service.events.event_processor import (
    EventProcessor,
    EventProcessorException
)

class ModelException(EventProcessorException):
    pass

class Model(EventProcessor):
    """
    We think of a Model as a representation or view that is built by processing event after event

    Methods
    -------    
    process_event(event: Event)
        Process the event so that the model can be updated accordingly        
    clone()
        Return a new copy of the model
    """

    def process_event(self, event: Event):
        raise NotImplementedError

    def clone(self):
        raise NotImplementedError
