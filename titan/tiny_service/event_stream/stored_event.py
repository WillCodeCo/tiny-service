##
# AUTOGENERATED CODE FILE
##
# from titan.tuple_class_codegen import TupleField, TupleClassCodegen
# 
# 
# def generate_code():
#     yield from TupleClassCodegen.generate_imports()
#     yield from TupleClassCodegen.generate_code('StoredEvent', [ TupleField.str('event_type'),
#                                                                 TupleField.bytes('event_bytes') ])
# 
##
import typing
import msgpack
import io

class StoredEvent(tuple):
    """Tuple Class definition for StoredEvent"""

    def __new__(cls, event_type: str, event_bytes: bytes):
        try:
            assert isinstance(event_type, str), f'Expected `event_type` to be of type `str` not `{type(event_type)}`'
            assert isinstance(event_bytes, bytes), f'Expected `event_bytes` to be of type `bytes` not `{type(event_bytes)}`'
            return super().__new__(cls, (event_type, event_bytes))
        except AssertionError as e:
            raise ValueError(str(e))

    @classmethod
    def tuple_type(cls) -> str:
        return cls.__name__

    @classmethod
    def create_from_tuple(cls, tuple_value: tuple):
        if not(isinstance(tuple_value, tuple)) or len(tuple_value) != 2:
            raise ValueError
        return cls(event_type=tuple_value[0], event_bytes=tuple_value[1])

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

    def event_type(self) -> str:
        return self[0]

    def event_bytes(self) -> bytes:
        return self[1]

    def serialize_to_bytes(self):
        return msgpack.packb(self, use_bin_type=True)

    def serialize_to_dict(self):
        return {
            'event_type': self.event_type(),
            'event_bytes': self.event_bytes(),
        }
