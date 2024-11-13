import ulid
import time

class Event:
    """Event base class"""

    @classmethod
    def create_event_id(cls):
        return str(ulid.from_timestamp(time.time()))

    @classmethod
    def create_event_id_with_timestamp(cls, timestamp: int):
        return str(ulid.from_timestamp(timestamp/1000))

    @classmethod
    def timestamp_from_event_id(cls, event_id: str):
        return ulid.parse(event_id).timestamp().int

    @classmethod
    def create(cls):
        raise NotImplementedError

    @classmethod
    def create_with_timestamp(cls, timestamp: int):
        raise NotImplementedError

    @classmethod
    def event_type(cls):
        raise NotImplementedError

    def event_id(self) -> str:
        raise NotImplementedError

    def timestamp(self):
        raise NotImplementedError
