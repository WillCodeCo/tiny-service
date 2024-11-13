from titan.tiny_service.events.event import Event
from titan.tiny_service.commands.command import Command
from titan.tiny_service.deprecated import state_machine
from titan.tiny_service.commands.command_translator import CommandTranslator, CommandTranslatorException



class EventToCommandTranslatorMachine(CommandTranslator):
    def __init__(self, initial_state_id, context):
        self._state_machine = state_machine.StateMachine(initial_state_id)
        self._context = context

    def state_machine(self):
        return self._state_machine

    def context(self):
        return self._context

    def translate_event_into_commands(self, event: Event):
        next_state_id = getattr(self, f"next_state_from_{self._state_machine.current_state_id()}")(self.context(), event)
        context_transaction = getattr(self, f"context_transaction_in_{self._state_machine.current_state_id()}")(next_state_id, self.context(), event)
        translated_commands = getattr(self, f"translate_event_in_{self._state_machine.current_state_id()}")(next_state_id, self.context(), context_transaction, event)
        if next_state_id:
            self.state_machine().enter(next_state_id, event)
        context_transaction.apply(self.context(), **context_transaction.params())
        return translated_commands

    def ensure_can_translate_event(self, event: Event):
        try:
            # if command cannot be translated, then this will raise an exception
            next_state_id = getattr(self, f"next_state_from_{self._state_machine.current_state_id()}")(self.context(), event)
            context_transaction = getattr(self, f"context_transaction_in_{self._state_machine.current_state_id()}")(next_state_id, self.context(), event)
            translated_commands = getattr(self, f"translate_event_in_{self._state_machine.current_state_id()}")(next_state_id, self.context(), context_transaction, event)
            context_transaction.ensure_can_apply(self.context(), **context_transaction.params())
            return True
        except Exception as e:
            raise CommandTranslatorException(f"Cannot translate event `{event}` in state `{self._state_machine.current_state_id()}`: {e}")


