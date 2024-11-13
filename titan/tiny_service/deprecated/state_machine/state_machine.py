class StateMachineException(Exception):
    pass

class StateMachineTransition(tuple):
    def __new__(cls, transition_id: int, source_state_id: str, dest_state_id: str, event: tuple):
        return super().__new__(cls, (transition_id, source_state_id, dest_state_id, event))

    def transition_id(self):
        return self[0]

    def source_state_id(self):
        return self[1]

    def dest_state_id(self):
        return self[2]

    def event(self):
        return self[3]

class StateMachineInitialTransition(StateMachineTransition):
    def __new__(cls, initial_state_id: str):
        return super().__new__(cls, 0, None, initial_state_id, None)


class StateMachine:
    def __init__(self, initial_state_id):
        self._current_state_id = initial_state_id
        self._last_transition = StateMachineInitialTransition(self._current_state_id)

    def _create_transition(self, dest_state_id, event):
        return StateMachineTransition(self._last_transition.transition_id()+1, self._current_state_id, dest_state_id, event)

    def enter(self, state_id, event):
        self._last_transition = self._create_transition(state_id, event)
        self._current_state_id = state_id

    def is_in(self, state_id):
        return self._current_state_id == state_id

    def current_state_id(self):
        return self._current_state_id

    def current_state(self):
        return (self._current_state_id, self._last_transition.transition_id())

    def last_transition(self):
        return self._last_transition
