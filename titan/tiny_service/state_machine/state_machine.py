class State:
    """
    Represent a state in a StateMachine. The developer should make a subclass for each state in the application.
    """
    pass


class StateMachine:
    """
    A simple implementation of a StateMachine

    States are represented by classes (not instances). The developer should subclass `State` for
    each state that is required.

    """
    def __init__(self, initial_state: State):
        self._current_state = initial_state
        self._transition_count = 0

    def enter(self, state: State):
        self._current_state = state
        self._transition_count += 1

    def is_in(self, state: State):
        return self._current_state == state

    def current_state(self):
        return self._current_state

    def transition_count(self):
        return self._transition_count


class StateMachineContext:
    """
    Provide some extra variables to augment the power of a StateMachine and to help fight against state-explosion.

    A StateMachineContext object can have any form provided it provides a clone() method.

    In practice it is better to keep it as simple as possible.
    """
    def clone(self):
        raise NotImplementedError
