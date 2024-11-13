import ulid
import time

class Command:
    """Command base class"""

    @classmethod
    def create_command_id(cls):
        return str(ulid.from_timestamp(time.time()))

    @classmethod
    def timestamp_from_command_id(cls, command_id: str):
        return ulid.parse(command_id).timestamp().int

    @classmethod
    def create(cls):
        raise NotImplementedError

    @classmethod
    def command_type(cls):
        raise NotImplementedError

    def command_id(self) -> str:
        raise NotImplementedError

    def timestamp(self):
        raise NotImplementedError