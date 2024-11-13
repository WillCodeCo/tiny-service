import struct
import msgpack
from titan.tiny_service.event_stream.stored_event import StoredEvent


class EventStreamException(Exception):
    pass


class EventStream:
    def __init__(self, metadata: dict):
        self._metadata = metadata
        self._events = []

    def metadata(self):
        return self._metadata

    def write_event(self, event):
        self._events.append(event)

    def events(self):
        return (event for event in self._events)

    def __eq__(self, other):
        if isinstance(other, EventStream):
            return (self.metadata() == other.metadata()) and all(event_a == event_b for event_a, event_b in itertools.zip_longest(self.events(), other.events(), fillvalue=object()))
        return NotImplemented


class _FileEventStreamEOFException(Exception):
    pass

class EventStreamFileReader:
    def __init__(self, file_obj):
        self._file_obj = file_obj
        self._metadata = self._read_metadata(file_obj)

    @classmethod
    def deserialize_event(cls, event_type: str, event_bytes: bytes):
        raise NotImplementedError("deserialize_event() needs to be implemented in a subclass of EventStreamFileReader")

    @classmethod
    def _read_metadata(cls, file_obj):
        try:
            file_obj.seek(0)
            len_bytes = file_obj.read(4)
            if len_bytes == b'':
                raise EventStreamException(f"Reached EOF while trying to read event-stream metadata")
            metadata_len = struct.unpack("!i", len_bytes)[0]
            return dict(msgpack.unpackb(file_obj.read(metadata_len), raw=False))
        except Exception as e:
            raise EventStreamException(f"Failed to read event-stream metadata due to exception: {e}")


    @classmethod
    def _read_next_event(cls, file_obj):
        try:
            len_bytes = file_obj.read(4)
            if len_bytes == b'':
                raise _FileEventStreamEOFException()            
            event_len = struct.unpack("!i", len_bytes)[0]
            stored_event = StoredEvent.create_from_bytes(file_obj.read(event_len))
            return cls.deserialize_event(stored_event.event_type(), stored_event.event_bytes())
        except _FileEventStreamEOFException:
            raise
        except EventStreamException:
            raise
        except Exception as e:
            raise EventStreamException(f"Failed to read event due to exception: {type(e)}: {e}")

    @classmethod
    def read_events(cls, file_obj):
        # we dont care about the metadata, but this will move the cursor to the right place
        cls._read_metadata(file_obj)
        cursor = file_obj.tell()
        while True:
            try:
                file_obj.seek(cursor)
                event = cls._read_next_event(file_obj)
                cursor = file_obj.tell()
                yield event
            except _FileEventStreamEOFException:
                break

    def metadata(self):
        return self._metadata

    def events(self):
        yield from self.read_events(self._file_obj)



class EventStreamFileWriter:
    def __init__(self, file_obj, metadata: dict):
        self._file_obj = file_obj
        self._metadata = metadata
        self._write_metadata(file_obj, metadata)

    @classmethod
    def _write_metadata(cls, file_obj, metadata: dict):
        file_obj.seek(0)
        metadata_bytes = msgpack.packb(metadata, use_bin_type=True)
        len_prefix = struct.pack("!i", len(metadata_bytes))
        file_obj.write(len_prefix+metadata_bytes)

    @classmethod
    def _write_event(cls, file_obj, event):
        stored_event = StoredEvent(event.event_type(), event.serialize_to_bytes())
        stored_event_bytes = stored_event.serialize_to_bytes()
        len_prefix = struct.pack("!i", len(stored_event_bytes))
        file_obj.write(len_prefix+stored_event_bytes)

    def metadata(self):
        return self._metadata

    def write_event(self, event):
        self._write_event(self._file_obj, event)

