##
# AUTOGENERATED CODE FILE
##
# from titan.tiny_service.events.event_class_codegen import EventField, EventClassCodegen
# 
# def generate_code():
#     yield from EventClassCodegen.generate_imports()
#     yield from EventClassCodegen.generate_code('DummyStartedEvent', [])
#     yield from EventClassCodegen.generate_code('DummyNoStateChangeEvent', [])
#     yield from EventClassCodegen.generate_code('DummyStateXEvent', [])
#     yield from EventClassCodegen.generate_code('DummyStateYEvent', [])
#     yield from EventClassCodegen.generate_code('DummyStateZEvent', [])
#     yield from EventClassCodegen.generate_code('DummyFinishedEvent', [])
#     yield from EventClassCodegen.generate_code('DummyEvent', [EventField.int('seq')])
##
import typing
import msgpack
import io

from titan.tiny_service.events import Event

class DummyStartedEvent(tuple, Event):
    """Tuple Class definition for DummyStartedEvent"""

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

class DummyNoStateChangeEvent(tuple, Event):
    """Tuple Class definition for DummyNoStateChangeEvent"""

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

class DummyStateXEvent(tuple, Event):
    """Tuple Class definition for DummyStateXEvent"""

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

class DummyStateYEvent(tuple, Event):
    """Tuple Class definition for DummyStateYEvent"""

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

class DummyStateZEvent(tuple, Event):
    """Tuple Class definition for DummyStateZEvent"""

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

class DummyFinishedEvent(tuple, Event):
    """Tuple Class definition for DummyFinishedEvent"""

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

class DummyEvent(tuple, Event):
    """Tuple Class definition for DummyEvent"""

    def __new__(cls, event_id: str, seq: int):
        try:
            assert isinstance(event_id, str), f'Expected `event_id` to be of type `str` not `{type(event_id)}`'
            assert isinstance(seq, int), f'Expected `seq` to be of type `int` not `{type(seq)}`'
            return super().__new__(cls, (event_id, seq))
        except AssertionError as e:
            raise ValueError(str(e))

    @classmethod
    def tuple_type(cls) -> str:
        return cls.__name__

    @classmethod
    def create_from_tuple(cls, tuple_value: tuple):
        if not(isinstance(tuple_value, tuple)) or len(tuple_value) != 2:
            raise ValueError
        return cls(event_id=tuple_value[0], seq=tuple_value[1])

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

    def seq(self) -> int:
        return self[1]

    def serialize_to_bytes(self):
        return msgpack.packb(self, use_bin_type=True)

    def serialize_to_dict(self):
        return {
            'event_id': self.event_id(),
            'seq': self.seq(),
        }

    @classmethod
    def create(cls, seq: int):
        return cls(Event.create_event_id(), seq)

    @classmethod
    def create_with_timestamp(cls, timestamp: int, seq: int):
        return cls.create_from_tuple( (Event.create_event_id_with_timestamp(timestamp), seq) )

    @classmethod
    def event_type(cls):
        return cls.__name__

    def timestamp(self):
        return Event.timestamp_from_event_id(self.event_id())
