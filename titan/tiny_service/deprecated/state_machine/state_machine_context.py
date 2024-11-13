class StateMachineContextTransaction:
    def __init__(self, **params):
        self._params = params

    @staticmethod
    def apply(context, **params):
        raise NotImplementedError
        
    @staticmethod
    def ensure_can_apply(context, **params):
        return True

    def params(self):
        return self._params


class DoNothingTransaction(StateMachineContextTransaction):
    @staticmethod
    def apply(context):
        pass

    @staticmethod
    def ensure_can_apply(context):
        return True

class StateMachineContext:
    DoNothingTransaction = DoNothingTransaction
    def __init__(self):
        pass

