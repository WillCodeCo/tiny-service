from titan.tuple_class_codegen import (
    TupleField as CommandField,
    TupleClassCodegen
)



class CommandClassCodegen(TupleClassCodegen):
    @classmethod
    def generate_imports(cls):
        yield from super().generate_imports()
        yield "from titan.tiny_service.commands import Command"
        yield ""

    @classmethod
    def generate_code(cls, command_type, tuple_fields):
        construction_values = ['Command.create_command_id()'] + cls.field_names(tuple_fields)
        yield from super().generate_code(   class_name=f"{command_type}",
                                            tuple_fields=[CommandField.str('command_id')] + tuple_fields,
                                            additional_parent_classes=['Command']  )
        yield ""
        yield f"    @classmethod"
        yield f"    def create({cls.function_definition_parameters_string(['cls'], tuple_fields)}):"
        yield f"        return cls{cls.tuple_value(construction_values)}"
        yield ""
        yield "    @classmethod"
        yield "    def command_type(cls):"
        yield "        return cls.__name__"
        yield ""
        yield f"    def timestamp(self):"
        yield f"        return Command.timestamp_from_command_id(self.command_id())"
        yield ""

