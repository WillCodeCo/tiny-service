import asyncio
import collections

class _SubscriptionBuffer:
    def __init__(self):
        self._item_buffer = collections.deque()
        self._new_item_future = None
        self._cancelled = False
        self._exception = None

    def _set_future_result(self, item):
        if (self._new_item_future is not None) and (not self._new_item_future.done()):
            self._new_item_future.set_result(item)

    async def _wait_new_item(self):
        try:
            if (self._new_item_future is None) or (self._new_item_future.done()):
                self._new_item_future = asyncio.get_running_loop().create_future()
            return await asyncio.shield(self._new_item_future)
        except asyncio.CancelledError:
            # if caller is cancelled we should cancel the buffer
            self.cancel()
            raise

    def has_exception(self):
        return (self._exception is not None)

    def exception(self):
        if self.cancelled():
            raise asyncio.CancelledError
        else:
            return self._exception

    def cancelled(self):
        return self._cancelled

    def set_exception(self, exception):
        if (self.cancelled()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.set_exception() cannot be called because the queue has been cancelled")
        elif (self.has_exception()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.set_exception() cannot be called because the queue has already been injected with an exception")
        else:
            self._exception = exception
            self._set_future_result(None)

    def cancel(self):
        if (self.cancelled()):
            pass
        elif (self.has_exception()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.cancel() cannot be called because an exception has already been set")
        else:
            self._cancelled = True
            self._set_future_result(None)

    def put(self, item):
        self._set_future_result(item)
        self._item_buffer.append(item)


    async def get(self):
        while True:
            try:
                return self._item_buffer.popleft()
            except IndexError:
                if (self.cancelled()):
                    raise asyncio.CancelledError
                elif (self.has_exception()):
                    raise self.exception()
                else:
                    item = await self._wait_new_item()
                    if item is None:
                        if (self.has_exception()):
                            raise self.exception()
                        elif (self.cancelled()):
                            raise asyncio.CancelledError
                        raise asyncio.InvalidStateError(f"{self.__class__.__name__}.get() got a NONE value despite the buffer not being cancelled or an exception being raised.")
                    continue





class _AsyncSubscriber:
    def __init__(self, subscription_buffer):
        self._subscription_buffer = subscription_buffer

    def has_exception(self):
        return self._subscription_buffer.has_exception()

    def cancelled(self):
        return self._subscription_buffer.cancelled()

    def exception(self):
        return self._subscription_buffer.exception()

    def set_exception(self, exception):
        self._subscription_buffer.set_exception(exception)

    def cancel(self):
        self._subscription_buffer.cancel()

    async def get(self):
        return await self._subscription_buffer.get()


class AsyncPubSub:
    def __init__(self):
        self._subscribers = set()
        self._subscription_buffers = {}
        self._cancelled = False
        self._exception = None

    def has_exception(self):
        return (self._exception is not None)

    def exception(self):
        if self.cancelled():
            raise asyncio.CancelledError
        else:
            return self._exception

    def cancelled(self):
        return self._cancelled

    def create_subscriber(self):
        if (self.has_exception()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.create_subscriber() cannot be called because an exception has been set")
        elif (self.cancelled()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.create_subscriber() cannot be called because it has been cancelled")
        else:
            subscription_buffer = _SubscriptionBuffer()
            subscriber = _AsyncSubscriber(subscription_buffer)
            self._subscribers.add(subscriber)
            self._subscription_buffers[subscriber] = subscription_buffer
            return subscriber

    def unsubscribe(self, subscriber):
        if (self.has_exception()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.unsubscribe() cannot be called because an exception has been set")
        elif (self.cancelled()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.unsubscribe() cannot be called because it has been cancelled")
        else:
            subscriber.cancel()
            del self._subscription_buffers[subscriber]       
            self._subscribers.remove(subscriber)

    async def publish(self, item):
        if (self.has_exception()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.publish() cannot be called because an exception has been set")
        elif (self.cancelled()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.publish() cannot be called because it has been cancelled")
        else:
            for subscription_buffer in self._subscription_buffers.values():
                subscription_buffer.put(item)
            # yield
            await asyncio.sleep(0)


    def set_exception(self, exception):
        if (self.cancelled()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.set_exception() cannot be called because it has been cancelled")
        elif (self.has_exception()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.set_exception() cannot be called because it has already been injected with an exception")
        else:
            self._exception = exception
            for subscriber in self._subscribers:
                subscriber.set_exception(exception)

    def cancel(self):
        if (self.cancelled()):
            pass
        elif (self.has_exception()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.cancel() cannot be called because an exception has already been set")
        else:
            self._cancelled = True
            for subscriber in self._subscribers:
                subscriber.cancel()

