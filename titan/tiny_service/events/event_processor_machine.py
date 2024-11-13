from __future__ import annotations # postpone evaluation of type annotations (will be default in Python 3.10)
from titan.tiny_service.events.event import Event
from titan.tiny_service.state_machine import (
    State,
    StateMachine,
    StateMachineContext
)

class EventProcessorMachineException(Exception):
    pass


class EventProcessorMachineState(State):
    @classmethod
    def next_state(cls, context: StateMachineContext, event: Event):
        raise NotImplementedError

    @classmethod
    def next_context(cls, next_state: EventProcessorMachineState, context: StateMachineContext, event: Event):
        raise NotImplementedError

    @classmethod
    def next_output(cls, next_state: EventProcessorMachineState, context: StateMachineContext, next_context: StateMachineContext, event: Event):
        raise NotImplementedError


class EventProcessorMachine:
    def __init__(self, initial_state: EventProcessorMachineState, context: StateMachineContext):
        self._state_machine = StateMachine(initial_state)
        self._context = context

    def state_machine(self):
        return self._state_machine

    def context(self):
        return self._context

    def process_event(self, event: Event):
        try:
            next_state = self.state_machine().current_state().next_state(self.context(), event)
            next_context = self.state_machine().current_state().next_context(next_state, self.context(), event)
            output = self.state_machine().current_state().next_output(next_state, self.context(), next_context, event)
            self.state_machine().enter(next_state)
            self._context = next_context
            return output
        except Exception as e:
            raise EventProcessorMachineException(f"Cannot process event `{event}` in state `{self._state_machine.current_state()}`: {e}")

