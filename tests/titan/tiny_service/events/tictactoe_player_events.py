##
# AUTOGENERATED CODE FILE
##
# from titan.tiny_service.events.event_class_codegen import EventField, EventClassCodegen
# 
# def generate_code():
#     yield from EventClassCodegen.generate_imports()
#     yield from EventClassCodegen.generate_code('PlayerXPlacedChipEvent', [  EventField.int('col'),
#                                                                             EventField.int('row'),   ])
#     yield from EventClassCodegen.generate_code('PlayerOPlacedChipEvent', [  EventField.int('col'),
#                                                                             EventField.int('row'),   ])
#     yield from EventClassCodegen.generate_code('PlayerXShookBoardInAngerEvent', [])
#     yield from EventClassCodegen.generate_code('PlayerOShookBoardInAngerEvent', [])
#     yield f"EVENT_TYPES = (PlayerXPlacedChipEvent, PlayerOPlacedChipEvent, PlayerXShookBoardInAngerEvent, PlayerOShookBoardInAngerEvent)"
##
import typing
import msgpack
import io

from titan.tiny_service.events import Event

class PlayerXPlacedChipEvent(tuple, Event):
    """Tuple Class definition for PlayerXPlacedChipEvent"""

    def __new__(cls, event_id: str, col: int, row: int):
        try:
            assert isinstance(event_id, str), f'Expected `event_id` to be of type `str` not `{type(event_id)}`'
            assert isinstance(col, int), f'Expected `col` to be of type `int` not `{type(col)}`'
            assert isinstance(row, int), f'Expected `row` to be of type `int` not `{type(row)}`'
            return super().__new__(cls, (event_id, col, row))
        except AssertionError as e:
            raise ValueError(str(e))

    @classmethod
    def tuple_type(cls) -> str:
        return cls.__name__

    @classmethod
    def create_from_tuple(cls, tuple_value: tuple):
        if not(isinstance(tuple_value, tuple)) or len(tuple_value) != 3:
            raise ValueError
        return cls(event_id=tuple_value[0], col=tuple_value[1], row=tuple_value[2])

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

    def col(self) -> int:
        return self[1]

    def row(self) -> int:
        return self[2]

    def serialize_to_bytes(self):
        return msgpack.packb(self, use_bin_type=True)

    def serialize_to_dict(self):
        return {
            'event_id': self.event_id(),
            'col': self.col(),
            'row': self.row(),
        }

    @classmethod
    def create(cls, col: int, row: int):
        return cls(Event.create_event_id(), col, row)

    @classmethod
    def create_with_timestamp(cls, timestamp: int, col: int, row: int):
        return cls.create_from_tuple( (Event.create_event_id_with_timestamp(timestamp), col, row) )

    @classmethod
    def event_type(cls):
        return cls.__name__

    def timestamp(self):
        return Event.timestamp_from_event_id(self.event_id())

class PlayerOPlacedChipEvent(tuple, Event):
    """Tuple Class definition for PlayerOPlacedChipEvent"""

    def __new__(cls, event_id: str, col: int, row: int):
        try:
            assert isinstance(event_id, str), f'Expected `event_id` to be of type `str` not `{type(event_id)}`'
            assert isinstance(col, int), f'Expected `col` to be of type `int` not `{type(col)}`'
            assert isinstance(row, int), f'Expected `row` to be of type `int` not `{type(row)}`'
            return super().__new__(cls, (event_id, col, row))
        except AssertionError as e:
            raise ValueError(str(e))

    @classmethod
    def tuple_type(cls) -> str:
        return cls.__name__

    @classmethod
    def create_from_tuple(cls, tuple_value: tuple):
        if not(isinstance(tuple_value, tuple)) or len(tuple_value) != 3:
            raise ValueError
        return cls(event_id=tuple_value[0], col=tuple_value[1], row=tuple_value[2])

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

    def col(self) -> int:
        return self[1]

    def row(self) -> int:
        return self[2]

    def serialize_to_bytes(self):
        return msgpack.packb(self, use_bin_type=True)

    def serialize_to_dict(self):
        return {
            'event_id': self.event_id(),
            'col': self.col(),
            'row': self.row(),
        }

    @classmethod
    def create(cls, col: int, row: int):
        return cls(Event.create_event_id(), col, row)

    @classmethod
    def create_with_timestamp(cls, timestamp: int, col: int, row: int):
        return cls.create_from_tuple( (Event.create_event_id_with_timestamp(timestamp), col, row) )

    @classmethod
    def event_type(cls):
        return cls.__name__

    def timestamp(self):
        return Event.timestamp_from_event_id(self.event_id())

class PlayerXShookBoardInAngerEvent(tuple, Event):
    """Tuple Class definition for PlayerXShookBoardInAngerEvent"""

    def __new__(cls, event_id: str):
        try:
            assert isinstance(event_id, str), f'Expected `event_id` to be of type `str` not `{type(event_id)}`'
            return super().__new__(cls, (event_id, ))
        except AssertionError as e:
            raise ValueError(str(e))

    @classmethod
    def tuple_type(cls) -> str:
        return cls.__name__

    @classmethod
    def create_from_tuple(cls, tuple_value: tuple):
        if not(isinstance(tuple_value, tuple)) or len(tuple_value) != 1:
            raise ValueError
        return cls(event_id=tuple_value[0])

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

    def serialize_to_bytes(self):
        return msgpack.packb(self, use_bin_type=True)

    def serialize_to_dict(self):
        return {
            'event_id': self.event_id(),
        }

    @classmethod
    def create(cls):
        return cls(Event.create_event_id(), )

    @classmethod
    def create_with_timestamp(cls, timestamp: int):
        return cls.create_from_tuple( (Event.create_event_id_with_timestamp(timestamp), ) )

    @classmethod
    def event_type(cls):
        return cls.__name__

    def timestamp(self):
        return Event.timestamp_from_event_id(self.event_id())

class PlayerOShookBoardInAngerEvent(tuple, Event):
    """Tuple Class definition for PlayerOShookBoardInAngerEvent"""

    def __new__(cls, event_id: str):
        try:
            assert isinstance(event_id, str), f'Expected `event_id` to be of type `str` not `{type(event_id)}`'
            return super().__new__(cls, (event_id, ))
        except AssertionError as e:
            raise ValueError(str(e))

    @classmethod
    def tuple_type(cls) -> str:
        return cls.__name__

    @classmethod
    def create_from_tuple(cls, tuple_value: tuple):
        if not(isinstance(tuple_value, tuple)) or len(tuple_value) != 1:
            raise ValueError
        return cls(event_id=tuple_value[0])

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

    def serialize_to_bytes(self):
        return msgpack.packb(self, use_bin_type=True)

    def serialize_to_dict(self):
        return {
            'event_id': self.event_id(),
        }

    @classmethod
    def create(cls):
        return cls(Event.create_event_id(), )

    @classmethod
    def create_with_timestamp(cls, timestamp: int):
        return cls.create_from_tuple( (Event.create_event_id_with_timestamp(timestamp), ) )

    @classmethod
    def event_type(cls):
        return cls.__name__

    def timestamp(self):
        return Event.timestamp_from_event_id(self.event_id())

EVENT_TYPES = (PlayerXPlacedChipEvent, PlayerOPlacedChipEvent, PlayerXShookBoardInAngerEvent, PlayerOShookBoardInAngerEvent)