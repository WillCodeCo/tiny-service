import asyncio
import collections

class AsyncQueue:
    """
    A wrapper for asyncio.Queue that allows the producer to signal to the consumer that it was cancelled or an exception occurred.
    """
    def __init__(self):
        self._queue = asyncio.Queue(maxsize=1)
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

    async def put(self, item):
        if (self.cancelled()):
            raise asyncio.InvalidStateError("AsyncQueue.put() cannot be called because the queue has been cancelled")
        elif (self.has_exception()):
            raise asyncio.InvalidStateError("AsyncQueue.put() cannot be called because the queue has been injected with an exception")
        else:
            await self._queue.put(item)

    async def get(self):
        if (self.cancelled()):
            raise asyncio.CancelledError
        elif (self.has_exception()):
            raise self.exception()
        else:
            item = await self._queue.get()
            if item is None:
                if (self.has_exception()):
                    raise self.exception()
                elif (self.cancelled()):
                    raise asyncio.CancelledError
                raise asyncio.InvalidStateError("AsyncQueue.get() got a NONE value in the queue despite the buffer not being cancelled or an exception being raised.")
            # otherwise
            return item

    def set_exception(self, exception):
        if (self.cancelled()):
            raise asyncio.InvalidStateError("AsyncQueue.set_exception() cannot be called because the queue has been cancelled")
        elif (self.has_exception()):
            raise asyncio.InvalidStateError("AsyncQueue.set_exception() cannot be called because the queue has already been injected with an exception")
        else:
            self._exception = exception
            if self._queue.empty():
                self._queue.put_nowait(None)

    def cancel(self):
        if (self.cancelled()):
            pass
        elif (self.has_exception()):
            raise asyncio.InvalidStateError("AsyncQueue.cancel() cannot be called because the queue has already been injected with an exception")
        else:
            self._cancelled = True
            if self._queue.empty():
                self._queue.put_nowait(None)

    def full(self):
        return self._queue.full()

    def empty(self):
        return self._queue.empty()


class AsyncPeekableQueue:
    def __init__(self):
        self._exception = None
        self._cancelled = False
        self._item_available_future = asyncio.get_running_loop().create_future()
        self._item_popped_future = None

    def has_exception(self):
        return (self._exception is not None)

    def exception(self):
        if self.cancelled():
            raise asyncio.CancelledError
        else:
            return self._exception

    def cancelled(self):
        return self._cancelled

    def empty(self):
        return (not self._item_available_future.done())

    def full(self):
        return (not self.empty()) and (self._item_popped_future) and (not self._item_popped_future.done())

    def _handle_item_available(self):
        self._item_popped_future = asyncio.get_running_loop().create_future()

    def _handle_item_popped(self):
        if (not self.cancelled()) and (not self.has_exception()):
            self._item_available_future = asyncio.get_running_loop().create_future()

    def set_exception(self, exception):
        if (self.cancelled()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.set_exception() cannot be called because the queue has been cancelled")
        elif (self.has_exception()):
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.set_exception() cannot be called because an exception has already been set")
        else:
            self._exception = exception
            if self._item_available_future:
                self._item_available_future.cancel()

    def cancel(self):
        if (self.cancelled()):
            pass
        elif (self.has_exception()):
            raise asyncio.InvalidStateError("AsyncQueue.cancel() cannot be called because the queue has already been injected with an exception")
        else:
            self._cancelled = True
            if self._item_available_future:
                self._item_available_future.cancel()


    async def wait_until_empty(self):
        try:
            await asyncio.shield(self._item_popped_future)
        except asyncio.CancelledError:
            if self.has_exception():
                raise self.exception()
            else:
                raise asyncio.CancelledError

    async def wait_until_full(self):
        try:
            await asyncio.shield(self._item_available_future)
        except asyncio.CancelledError:
            if self.has_exception():
                raise self.exception()
            else:
                raise asyncio.CancelledError

    async def put(self, item):
        while self.full():
            await self.wait_until_empty()
        self._item_available_future.set_result(item)
        self._handle_item_available()
        await asyncio.sleep(0)

    async def peek(self):
        if (self.has_exception()):
            raise self.exception()
        elif (self.cancelled()):
            raise asyncio.CancelledError
        else:
            while self.empty():
                await self.wait_until_full()
            return self._item_available_future.result()


    def pop(self):
        if self.full():
            result = self._item_available_future.result()
            self._item_popped_future.set_result(result)
            self._handle_item_popped()
            return result
        elif (self.cancelled()):
            raise asyncio.CancelledError
        elif (self.has_exception()):
            raise self.exception()
        elif self.empty():
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.pop() cannot be called because the queue is empty !")
        else:
            raise asyncio.InvalidStateError(f"{self.__class__.__name__}.pop() State should never have been reached")





# class AsyncPeekableQueue:
#     """
#     A queue primitive to allow a consumer to wait for a new value to be produced without removing it, i.e. we have peek()  and pop() semantics
#     """
#     def __init__(self):
#         self._queue = AsyncQueue()
#         self._queue_head_future = None

#     def has_exception(self):
#         return self._queue.has_exception()

#     def cancelled(self):
#         return self._queue.cancelled()

#     def exception(self):
#         return self._queue.exception()

#     def set_exception(self, exception):
#         if (self._queue_head_future is not None):
#             self._queue_head_future.set_result(None)
#         self._queue.set_exception(exception)


#     def cancel(self):
#         if (self._queue_head_future is not None):
#             self._queue_head_future.set_result(None)
#         self._queue.cancel()


#     def empty(self):
#         return (not self._queue_head_future.done())

#     async def peek(self):
#         if (self.has_exception()):
#             raise self.exception()
#         elif (self.cancelled()):
#             raise asyncio.CancelledError
#         else:
#             if self._queue_head_future is None:
#                 self._queue_head_future = asyncio.get_running_loop().create_future()
#                 item = await self._queue.get()
#                 if self.cancelled():
#                     raise asyncio.CancelledError
#                 else:
#                     self._queue_head_future.set_result(item)
#                     return item
#             else:
#                 return await self._queue_head_future

#     def pop(self):
#         if self.empty():
#             raise asyncio.InvalidStateError("AsyncPeekableQueue.pop() cannot be called because the queue is empty !")
#         else:
#             result = self._queue_head_future.result()
#             self._queue_head_future = None
#             return result

#     async def put(self, item):
#         await self._queue.put(item)







# class AsyncPeekableQueue:
#     def __init__(self):
#         self._queue = AsyncQueue()
#         self._next_item_available_future = None

#     def has_exception(self):
#         return self._queue.has_exception()

#     def exception(self):
#         return self._queue.exception()

#     def cancelled(self):
#         return self._queue.cancelled()

#     def set_exception(self, exception):
#         self._queue.set_exception(exception)

#     def cancel(self):
#         self._queue.cancel()

#     def empty(self):
#         return (self._next_item_available_future is None) or (not self._next_item_available_future.done())

#     def full(self):
#         return (self._next_item_available_future) and (self._next_item_available_future.done())

#     @classmethod
#     async def _wait_for_item_and_set_future(cls, item_queue, item_future):
#         try:
#             item = await item_queue.get()            
#             item_future.set_result(item)
#             return item
#         except asyncio.CancelledError:
#             item_future.set_result(None)
#             if (not item_queue.cancelled()):
#                 # propagate cancellation if the source queue was not cancelled
#                 raise
#         except Exception as e:
#             item_future.set_result(None)
#             raise


#     async def _wait_for_next_item(self):
#         if self._next_item_available_future is None:
#             self._next_item_available_future = asyncio.get_running_loop().create_future()
#             try:
#                 return await self._wait_for_item_and_set_future(self._queue, self._next_item_available_future)
#             except asyncio.CancelledError:
#                 pass#raise # propagate
#             except Exception:
#                 self._next_item_available_future = None
#         else:
#             return await asyncio.shield(self._next_item_available_future)


#     async def peek(self):
#         if (self.has_exception()):
#             raise self.exception()
#         elif (self.cancelled()):
#             raise asyncio.CancelledError
#         else:
#             if self.full():
#                 return self._next_item_available_future.result()
#             else:
#                 return await self._wait_for_next_item()


#     def pop(self):
#         if (self.full()):
#             result = self._next_item_available_future.result()
#             self._next_item_available_future = None
#             return result
#         elif (self.cancelled()):
#             raise asyncio.CancelledError
#         elif (self.has_exception()):
#             raise self.exception()
#         elif self.empty():
#             raise asyncio.InvalidStateError(f"{self.__class__.__name__}.pop() cannot be called because the queue is empty !")
#         else:
#             raise asyncio.InvalidStateError(f"{self.__class__.__name__}.pop() State should never have been reached")

#     async def put(self, item):
#         await self._queue.put(item)



class AsyncSharedQueue:
    def __init__(self, source_queue, num_consumers):
        self._source_queue = source_queue
        self._consumer_buffers = [collections.deque() for _ in range(num_consumers)]
        self._next_item_available_future = None

    def has_exception(self):
        return self._source_queue.has_exception()

    def exception(self):
        return self._source_queue.exception()

    def cancelled(self):
        return self._source_queue.cancelled()

    def set_exception(self, exception):
        self._source_queue.set_exception(exception)

    def cancel(self):
        self._source_queue.cancel()

    @classmethod
    def _distribute_item(cls, consumer_buffers, item):
        if (item is not None):
            for item_buffer in consumer_buffers:
                item_buffer.append(item)

    @classmethod
    async def _wait_for_item_and_distribute(cls, item_queue, item_future, consumer_buffers):
        try:
            item = await item_queue.get()
            cls._distribute_item(consumer_buffers, item)
            item_future.set_result(item)
        except asyncio.CancelledError:
            item_future.set_result(None)
            if (not item_queue.cancelled()):
                # propagate cancellation if the source queue was not cancelled
                raise
        except Exception as e:
            item_future.set_result(None)


    async def _wait_for_next_item_distribution(self):
        if (self._next_item_available_future is None) or (self._next_item_available_future.done()):
            self._next_item_available_future = asyncio.get_running_loop().create_future()
            await self._wait_for_item_and_distribute(self._source_queue, self._next_item_available_future, self._consumer_buffers)
        else:
            await asyncio.shield(self._next_item_available_future)


    async def get(self, consumer_index: int):
        while True:
            try:
                return self._consumer_buffers[consumer_index].popleft()
            except IndexError:
                await self._wait_for_next_item_distribution()
                if (self.cancelled()):
                    raise asyncio.CancelledError
                elif (self.has_exception()):
                    raise self.exception()
                else:
                    # yield to event loop
                    await asyncio.sleep(0)

