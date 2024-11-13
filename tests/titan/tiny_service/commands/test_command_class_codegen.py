import pytest
import logging
import importlib
import os
import tempfile
import ulid


logger = logging.getLogger(__name__)


def generate_codegen_code():
    yield "from titan.tiny_service.commands.command_class_codegen import CommandField, CommandClassCodegen"
    yield ""
    yield "def generate_code():"
    yield "    yield from CommandClassCodegen.generate_imports()"
    yield "    yield from CommandClassCodegen.generate_code('DummyBlaCommand', [   CommandField.int('some_arg'),"
    yield "                                                                        CommandField.bool('another_arg') ])"





def load_module(module_path):
    spec = importlib.util.spec_from_file_location("codegen_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def ensure_valid_command_class_module(file_path):
    module = load_module(file_path)
    timestamp = 89738974
    command_id = str(ulid.from_timestamp(timestamp/1000))
    command = module.DummyBlaCommand(command_id=command_id, some_arg=42, another_arg=True)
    assert type(command) == module.DummyBlaCommand
    assert command.command_type() == 'DummyBlaCommand'
    assert command.command_id() == command_id
    assert command.timestamp() == timestamp
    assert command.some_arg() == 42
    assert command.another_arg() == True
    assert str(command) == f"DummyBlaCommand('{command_id}', 42, True)"
    assert repr(command) == f"DummyBlaCommand('{command_id}', 42, True)"
    # Make sure we can create a command using the factory method which automatically creates a command_id value
    command = module.DummyBlaCommand.create(some_arg=69, another_arg=False)
    assert type(command) == module.DummyBlaCommand
    assert command.command_type() == 'DummyBlaCommand'
    assert type(command.command_id()) == str
    assert command.timestamp() == ulid.parse(command.command_id()).timestamp().int
    assert command.some_arg() == 69
    assert command.another_arg() == False
    assert str(command) == f"DummyBlaCommand('{command.command_id()}', 69, False)"
    assert repr(command) == f"DummyBlaCommand('{command.command_id()}', 69, False)"


def execute_codegen_script(target_dir):
    os.system(f"codegen --target-path={target_dir} -y")

def test_command_class():
    with tempfile.TemporaryDirectory() as working_dir:
        with open(os.path.join(working_dir, 'command_classes.py.codegen'), 'w') as f:
            f.write("\n".join(generate_codegen_code()))
        execute_codegen_script(working_dir)
        ensure_valid_command_class_module(os.path.join(working_dir, 'command_classes.py'))
