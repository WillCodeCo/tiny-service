import pytest
import logging
import importlib
import os
import tempfile
import ulid
import msgpack

logger = logging.getLogger(__name__)


def generate_codegen_code():
    yield "from titan.tiny_service.events.event_class_codegen import EventField, EventClassCodegen"
    yield ""
    yield "def generate_code():"
    yield "    yield from EventClassCodegen.generate_imports()"
    yield "    yield from EventClassCodegen.generate_code('SomethingHappenedEvent', [   EventField.int('some_int_value'),"
    yield "                                                                             EventField.bool('some_bool_value')  ])"





def load_module(module_path):
    spec = importlib.util.spec_from_file_location("codegen_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def ensure_valid_event_class_module(file_path):
    module = load_module(file_path)
    timestamp = 89738974
    event_id = str(ulid.from_timestamp(timestamp/1000))
    event = module.SomethingHappenedEvent(event_id=event_id, some_int_value=42, some_bool_value=True)
    assert type(event) == module.SomethingHappenedEvent
    assert event.event_type() == 'SomethingHappenedEvent'
    assert event.event_id() == event_id
    assert event.timestamp() == timestamp
    assert event.some_int_value() == 42
    assert event.some_bool_value() == True
    assert str(event) == f"SomethingHappenedEvent('{event_id}', 42, True)"
    assert repr(event) == f"SomethingHappenedEvent('{event_id}', 42, True)"
    # Make sure we can create a event using the factory method which automatically creates a event_id value
    event = module.SomethingHappenedEvent.create(some_int_value=69, some_bool_value=False)
    assert type(event) == module.SomethingHappenedEvent
    assert event.event_type() == 'SomethingHappenedEvent'
    assert type(event.event_id()) == str
    assert event.timestamp() == ulid.parse(event.event_id()).timestamp().int
    assert event.some_int_value() == 69
    assert event.some_bool_value() == False
    assert str(event) == f"SomethingHappenedEvent('{event.event_id()}', 69, False)"
    assert repr(event) == f"SomethingHappenedEvent('{event.event_id()}', 69, False)"
    # Make sure we can create a event using the factory method which automatically creates a event_id value for a given timestamp
    timestamp = 90820424
    event = module.SomethingHappenedEvent.create_with_timestamp(timestamp, some_int_value=12, some_bool_value=False)
    assert type(event) == module.SomethingHappenedEvent
    assert event.event_type() == 'SomethingHappenedEvent'
    assert str(ulid.parse(event.event_id())) == event.event_id()
    assert event.timestamp() == timestamp
    assert event.some_int_value() == 12
    assert event.some_bool_value() == False
    assert str(event) == f"SomethingHappenedEvent('{event.event_id()}', 12, False)"
    assert repr(event) == f"SomethingHappenedEvent('{event.event_id()}', 12, False)"


def execute_codegen_script(target_dir):
    os.system(f"codegen --target-path={target_dir} -y")

def test_event_class():
    with tempfile.TemporaryDirectory() as working_dir:
        with open(os.path.join(working_dir, 'event_classes.py.codegen'), 'w') as f:
            f.write("\n".join(generate_codegen_code()))
        execute_codegen_script(working_dir)
        ensure_valid_event_class_module(os.path.join(working_dir, 'event_classes.py'))
