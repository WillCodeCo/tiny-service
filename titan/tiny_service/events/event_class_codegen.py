from titan.tuple_class_codegen import (
    TupleField as EventField,
    TupleClassCodegen
)



class EventClassCodegen(TupleClassCodegen):

    @classmethod
    def generate_imports(cls):
        yield from super().generate_imports()
        yield "from titan.tiny_service.events import Event"
        yield ""

    @classmethod
    def generate_code(cls, event_type, tuple_fields):
        construction_values = ['Event.create_event_id()'] + cls.field_names(tuple_fields)
        yield from super().generate_code(   class_name=f"{event_type}",
                                            tuple_fields=[('event_id', str)] + tuple_fields,
                                            additional_parent_classes=['Event']  )
        yield f"    @classmethod"
        yield f"    def create({cls.function_definition_parameters_string(['cls'], tuple_fields)}):"
        yield f"        return cls{cls.tuple_value(construction_values)}"
        yield ""
        yield f"    @classmethod"
        yield f"    def create_with_timestamp({cls.function_definition_parameters_string(['cls', 'timestamp: int'], tuple_fields)}):"
        yield f"        return cls.create_from_tuple( {cls.tuple_value(['Event.create_event_id_with_timestamp(timestamp)'] + cls.field_names(tuple_fields))} )"
        yield ""
        yield "    @classmethod"
        yield "    def event_type(cls):"
        yield "        return cls.__name__"
        yield ""
        yield f"    def timestamp(self):"
        yield f"        return Event.timestamp_from_event_id(self.event_id())"
        yield ""

