from __future__ import annotations # postpone evaluation of type annotations (will be default in Python 3.10)
from titan.tiny_service.events.event import Event
from titan.tiny_service.state_machine import (
    State,
    StateMachine,
    StateMachineContext
)
from titan.tiny_service.events.event_processor_machine import (
    EventProcessorMachineException,
    EventProcessorMachineState,
    EventProcessorMachine
)
from titan.tiny_service.events.event_translator import (
    EventTranslatorException,
    EventTranslator
)


class EventTranslatorMachineContext(StateMachineContext):
    pass

class EventTranslatorMachineState(EventProcessorMachineState):
    @classmethod
    def translate_event(cls, next_state: EventProcessorMachineState, context: EventTranslatorMachineContext, next_context: EventTranslatorMachineContext, event: Event):
        raise NotImplementedError


class EventTranslatorMachine(EventTranslator, EventProcessorMachine):

    def translate_event(self, event: Event):
        """
        Translate an event into a list of other events.

        All-or-nothing semantics, either it succeeds or an exception is raised
        """
        try:
            new_state = self.state_machine().current_state().next_state(self.context(), event)
            new_context = self.state_machine().current_state().next_context(new_state, self.context(), event)
            translated_events = self.state_machine().current_state().translate_event(new_state, self.context(), new_context, event)
            cur_state = new_state
            cur_context = new_context
            # Now we also have to allow the statemachine to process the translated events too
            #  as these events can cause state changes and context mutations
            for event in translated_events:
                new_state = cur_state.next_state(cur_context, event)
                new_context = cur_state.next_context(new_state, cur_context, event)
                cur_state = new_state
                cur_context = new_context
            self.state_machine().enter(cur_state)
            self._context = cur_context
            return translated_events
        except Exception as e:
            raise EventTranslatorException(f"Cannot translate event `{event}` in state `{self.state_machine().current_state()}`: {e}")
