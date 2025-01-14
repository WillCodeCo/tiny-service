##
# AUTOGENERATED CODE FILE
##
# from titan.tiny_service.events.event_class_codegen import EventField, EventClassCodegen
# from titan.tiny_service.commands.command_class_codegen import CommandField, CommandClassCodegen
# 
# def generate_code():
#     yield "\n".join(set(EventClassCodegen.generate_imports()) | set(CommandClassCodegen.generate_imports()))
#     yield ""
#     yield from EventClassCodegen.generate_code('FoundPrimeSquareEvent', [EventField.int('prime_square')])
#     yield from CommandClassCodegen.generate_code('ProcessThisPrimeNumberCommand', [CommandField.int('some_number')])
##

import io
import msgpack
from titan.tiny_service.commands import Command
from titan.tiny_service.events import Event
import typing

class FoundPrimeSquareEvent(tuple, Event):
    """Tuple Class definition for FoundPrimeSquareEvent"""

    def __new__(cls, event_id: str, prime_square: int):
        try:
            assert isinstance(event_id, str), f'Expected `event_id` to be of type `str` not `{type(event_id)}`'
            assert isinstance(prime_square, int), f'Expected `prime_square` to be of type `int` not `{type(prime_square)}`'
            return super().__new__(cls, (event_id, prime_square))
        except AssertionError as e:
            raise ValueError(str(e))

    @classmethod
    def tuple_type(cls) -> str:
        return cls.__name__

    @classmethod
    def create_from_tuple(cls, tuple_value: tuple):
        if not(isinstance(tuple_value, tuple)) or len(tuple_value) != 2:
            raise ValueError
        return cls(event_id=tuple_value[0], prime_square=tuple_value[1])

    @classmethod
    def create_from_bytes(cls, tuple_bytes: bytes):
        return cls.create_from_tuple(msgpack.unpackb(tuple_bytes, use_list=False, raw=False))

    @classmethod
    def generate_from_stream(cls, buf: io.BytesIO):
        unpacker = msgpack.Unpacker(buf, use_list=False, raw=False)
        for unpacked in unpacker:
            yield cls.create_from_tuple(unpacked)

    def __str__(self):
        return f"{self.tuple_type()}{str(tuple(self))}"

    def __repr__(self):
        return f"{self.tuple_type()}{repr(tuple(self))}"

    def __eq__(self, other):
        return (type(self) == type(other)) and (tuple(self) == tuple(other))

    def __ne__(self, other):
        return (not (self == other))

    def __hash__(self):
        return hash(tuple(self))

    def event_id(self) -> str:
        return self[0]

    def prime_square(self) -> int:
        return self[1]

    def serialize_to_bytes(self):
        return msgpack.packb(self, use_bin_type=True)

    def serialize_to_dict(self):
        return {
            'event_id': self.event_id(),
            'prime_square': self.prime_square(),
        }

    @classmethod
    def create(cls, prime_square: int):
        return cls(Event.create_event_id(), prime_square)

    @classmethod
    def create_with_timestamp(cls, timestamp: int, prime_square: int):
        return cls.create_from_tuple( (Event.create_event_id_with_timestamp(timestamp), prime_square) )

    @classmethod
    def event_type(cls):
        return cls.__name__

    def timestamp(self):
        return Event.timestamp_from_event_id(self.event_id())

class ProcessThisPrimeNumberCommand(tuple, Command):
    """Tuple Class definition for ProcessThisPrimeNumberCommand"""

    def __new__(cls, command_id: str, some_number: int):
        try:
            assert isinstance(command_id, str), f'Expected `command_id` to be of type `str` not `{type(command_id)}`'
            assert isinstance(some_number, int), f'Expected `some_number` to be of type `int` not `{type(some_number)}`'
            return super().__new__(cls, (command_id, some_number))
        except AssertionError as e:
            raise ValueError(str(e))

    @classmethod
    def tuple_type(cls) -> str:
        return cls.__name__

    @classmethod
    def create_from_tuple(cls, tuple_value: tuple):
        if not(isinstance(tuple_value, tuple)) or len(tuple_value) != 2:
            raise ValueError
        return cls(command_id=tuple_value[0], some_number=tuple_value[1])

    @classmethod
    def create_from_bytes(cls, tuple_bytes: bytes):
        return cls.create_from_tuple(msgpack.unpackb(tuple_bytes, use_list=False, raw=False))

    @classmethod
    def generate_from_stream(cls, buf: io.BytesIO):
        unpacker = msgpack.Unpacker(buf, use_list=False, raw=False)
        for unpacked in unpacker:
            yield cls.create_from_tuple(unpacked)

    def __str__(self):
        return f"{self.tuple_type()}{str(tuple(self))}"

    def __repr__(self):
        return f"{self.tuple_type()}{repr(tuple(self))}"

    def __eq__(self, other):
        return (type(self) == type(other)) and (tuple(self) == tuple(other))

    def __ne__(self, other):
        return (not (self == other))

    def __hash__(self):
        return hash(tuple(self))

    def command_id(self) -> str:
        return self[0]

    def some_number(self) -> int:
        return self[1]

    def serialize_to_bytes(self):
        return msgpack.packb(self, use_bin_type=True)

    def serialize_to_dict(self):
        return {
            'command_id': self.command_id(),
            'some_number': self.some_number(),
        }


    @classmethod
    def create(cls, some_number: int):
        return cls(Command.create_command_id(), some_number)

    @classmethod
    def command_type(cls):
        return cls.__name__

    def timestamp(self):
        return Command.timestamp_from_command_id(self.command_id())
