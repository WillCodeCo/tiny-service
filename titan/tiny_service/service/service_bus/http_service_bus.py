import asyncio
import io
import time
import logging
import weakref
import hashlib
import base64
import aiohttp
from aiohttp import web
from titan.tiny_service.async_helper import (
    AsyncTaskRunner,
    AsyncTaskHelper,
    AsyncQueue,
    AsyncPubSub
)
from titan.tiny_service.service.service_bus import (
    ServiceBusClient,
    ServiceBusServer,
    ServiceBusException,
    EventMessageCache,
    EventMessageCacheException,
    CommandBusCacheException,
    CommandBusCache
)
from titan.tiny_service.service.service_bus import service_bus_messages

logger = logging.getLogger(__name__)


def system_timestamp():
    return int(time.time()*1000)

def hash_bytes(some_bytes: bytes):
    m = hashlib.sha256()
    m.update(some_bytes)
    return base64.urlsafe_b64encode(m.digest()).decode('utf-8')


class WSManager:
    def __init__(self, ws: web.WebSocketResponse):
        self._task_runner = None
        self._ws = ws
        self._ws_bytes_pub_sub = None
        self._ws_bytes_subscriber = None
        
    @classmethod
    async def _ws_bytes_receiver(cls,  ws: web.WebSocketResponse, ws_bytes_pub_sub: AsyncPubSub):
        try:
            while (not ws.closed):
                ws_message = await ws.receive()
                if ws_message.type in {web.WSMsgType.CLOSE, web.WSMsgType.CLOSING}:
                    break
                assert ws_message.type == web.WSMsgType.BINARY, f"Invalid websocket message type ({ws_message.type})"
                await ws_bytes_pub_sub.publish(ws_message.data)
        except ConnectionError as e:
            logger.error(f"Socket error in {cls.__name__}._ws_bytes_receiver(): {e}")
            raise ServiceBusException(f"Socket error in {cls.__name__}._ws_bytes_receiver(): {e}")
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout in {cls.__name__}._ws_bytes_receiver(): {e}")
            raise ServiceBusException(f"Timeout in {cls.__name__}._ws_bytes_receiver(): {e}")
        except AssertionError as e:
            logger.error(f"AssertionError in {cls.__name__}._ws_bytes_receiver(): {e}")
            raise ServiceBusException(f"AssertionError in {cls.__name__}._ws_bytes_receiver(): {e}")
        except Exception as e:
            logger.error(f"Unexpected exception `{type(e)}` in {cls.__name__}._ws_bytes_receiver(): {e}")
            raise ServiceBusException(f"Unexpected exception `{type(e)}` in {cls.__name__}._ws_bytes_receiver(): {e}")
        finally:
            # this makes sure that any waiters on a subcriber gets cancelled
            ws_bytes_pub_sub.cancel()
            if not ws.closed:
                await ws.close(code=4000)

    def is_closed(self):
        return self._ws.closed

    async def send_bytes(self, some_bytes: bytes):
        if (not self.active()):
            raise ServiceBusException(f"Cannot call {self.__class__.__name__}.send_bytes() because WSManager is not active")
        elif self.is_closed():
            raise ServiceBusException(f"Cannot call {self.__class__.__name__}.send_bytes() because websocket is closed.")
        try:
            await self._ws.send_bytes(some_bytes)
        except ConnectionError as e:
            raise ServiceBusException(f"Socket error in {self.__class__.__name__}.send_bytes(): {e}")
        except Exception as e:
            logger.error(f"Unexpected exception `{type(e)}` in {self.__class__.__name__}.send_bytes(): {e}")
            raise        

    async def receive_bytes(self):
        task = asyncio.create_task(self._ws_bytes_subscriber.get())
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.done():
                raise ServiceBusException(f"Failure to receive_bytes in {self.__class__.__name__} because the WSManager is closing !")
            else:
                await AsyncTaskHelper.cancel_and_wait(task)
                raise
            
    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        self._ws_bytes_pub_sub = AsyncPubSub()
        self._ws_bytes_subscriber = self._ws_bytes_pub_sub.create_subscriber()
        tasks = [
            asyncio.create_task(self._ws_bytes_receiver(self._ws, self._ws_bytes_pub_sub)),
        ]
        self._task_runner = AsyncTaskRunner(tasks)
        await self._task_runner.start()

    async def run(self):
        await self.start()
        await self.wait_closed()

    async def wait_closed(self):
        if self._task_runner:
            await self._task_runner.wait_closed()

    async def close(self):
        if self._task_runner:
            await self._task_runner.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        close_task = asyncio.create_task(self.close())
        try:
            await asyncio.shield(close_task)
        except asyncio.CancelledError:
            await close_task
            raise
        except Exception as e:
            logger.info(f"{self.__class__.__name__} is suppressing exception with type `{type(e)}` : {e}")





class HttpServiceBusServer(ServiceBusServer):
    EVENT_MESSAGE_CACHE_SIZE = 10000
    WEBSOCKET_HEARTBEAT = 1
    WEBSOCKET_MAX_MSG_SIZE = 16 * 1024 * 1024
    WEBSOCKET_READ_TIMEOUT = 5

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._endpoints = None
        self._task_runner = None
        self._app = web.Application()
        self._app['websockets'] = weakref.WeakSet() # keep track of objects without preventing garbage-collection
        self._app.add_routes([  web.get('/catchup-event-messages', self._get_catchup_events_handler),
                                web.get('/event-bus', self._get_event_bus_handler),
                                web.get('/command-bus', self._get_command_bus_handler)  ])
        self._command_bus_cache = CommandBusCache()
        self._event_message_cache = EventMessageCache(HttpServiceBusServer.EVENT_MESSAGE_CACHE_SIZE)
        self._event_message_pub_sub = AsyncPubSub()
        self._command_message_queue = AsyncQueue()
        self._command_receipt_message_queue = AsyncQueue()
        self._is_command_bus_reserved = False
        self._next_event_message_seq = 0

    def host(self):
        return self._host

    def port(self):
        return self._port

    def is_command_bus_reserved(self):
        return self._is_command_bus_reserved

    def endpoints(self):
        if (self._endpoints is None):
            raise ServiceBusException(f"No endpoints are available to be returned at the moment.")
        return self._endpoints

    def next_event_message_seq(self):
        return self._next_event_message_seq

    @classmethod
    async def _event_bus_receiver(cls,  ws_manager: WSManager):
        while (not ws_manager.is_closed()):
            msg_bytes = await ws_manager.receive_bytes()
            if msg_bytes:
                raise ServiceBusException(f"Did not expect to receive a message in {cls.__name__}._event_bus_receiver() !")

    @classmethod
    async def _event_bus_sender(cls, ws_manager: WSManager, event_message_pub_sub: AsyncPubSub):
        try:
            event_message_subscriber = event_message_pub_sub.create_subscriber()
            while (not ws_manager.is_closed()):
                event_message = await event_message_subscriber.get()               
                await ws_manager.send_bytes(event_message.serialize_to_bytes())
        finally:
            if not event_message_pub_sub.cancelled():
                event_message_pub_sub.unsubscribe(event_message_subscriber)


    @classmethod
    async def _manage_event_bus_ws(cls,  ws: web.WebSocketResponse, event_message_pub_sub: AsyncPubSub):
        async with WSManager(ws) as ws_manager:
            tasks = [
                asyncio.create_task(cls._event_bus_sender(ws_manager, event_message_pub_sub)),
                asyncio.create_task(cls._event_bus_receiver(ws_manager))
            ]
            async with AsyncTaskRunner(tasks) as task_runner:
                await task_runner.wait_closed()




    @classmethod
    async def _command_bus_get_receipt_for_command(cls, command_message: service_bus_messages.CommandMessage,
                                                        command_message_queue: AsyncQueue,
                                                        command_receipt_message_queue: AsyncQueue,
                                                        command_bus_cache: CommandBusCache):
        try:
            # have we seen the command before ?  is it cached ?
            is_fresh_command = (not command_bus_cache.has_command_message()) or (command_bus_cache.last_command_message() != command_message)
            is_cached_command = (command_bus_cache.has_command_receipt_message() and command_bus_cache.last_command_message() == command_message)
            # treat it based on whether we have seen it before and if it is cached or not
            if is_cached_command:
                await ws_manager.send_bytes(command_bus_cache.last_command_receipt_message().serialize_to_bytes()) 
            else:
                if is_fresh_command:
                    await command_message_queue.put(command_message)
                    command_bus_cache.save_command_message(command_message)
                # wait for receipt
                command_receipt_message = await command_receipt_message_queue.get()
                command_bus_cache.save_command_receipt_message(command_receipt_message)
                return command_receipt_message
        except CommandBusCacheException as e:
            raise ServiceBusException(f"command-bus-cache got corrupted in {cls.__name__}._command_bus_get_receipt_for_command: {e}")



    @classmethod
    async def _manage_command_bus_ws(cls,  ws: web.WebSocketResponse, command_message_queue: AsyncQueue, command_receipt_message_queue: AsyncQueue, command_bus_cache: CommandBusCache):
        try:
            async with WSManager(ws) as ws_manager:
                while (not ws_manager.is_closed()):
                    # wait for a command message
                    command_message = service_bus_messages.CommandMessage.create_from_bytes(await ws_manager.receive_bytes())
                    command_receipt_message = await cls._command_bus_get_receipt_for_command(   command_message,
                                                                                                command_message_queue,
                                                                                                command_receipt_message_queue,
                                                                                                command_bus_cache  )
                    await ws_manager.send_bytes(command_receipt_message.serialize_to_bytes())
        except ValueError:
            raise ServiceBusException(f"Failed to parse message in {cls.__name__}._manage_command_bus_ws()")
        finally:
            logger.debug(f"Exiting {cls.__name__}._manage_command_bus_ws()")



    async def _run_server(self):
        try:
            runner = web.AppRunner(self._app)
            await runner.setup()
            site = web.TCPSite(runner, host=self._host, port=self._port)
            await site.start()
            # Display the endpoints - useful if we choose a zero port number
            self._endpoints = [sock.getsockname() for sock in site._server.sockets]
            listening_eps = ', '.join([f"{ep[0]}:{ep[1]}" for ep in self._endpoints])
            logger.info(f"{self.__class__.__name__} is listening at:\t{listening_eps}")
            while True:
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Unexpected exception in {self.__class__.__name__}._run_server(): {e}")
        finally:
            logger.debug(f"Exiting {self.__class__.__name__}._run_server()")
            self._event_message_pub_sub.cancel()
            self._command_receipt_message_queue.cancel()
            self._command_message_queue.cancel()
            for ws in set(self._app['websockets']):
                if not ws.closed:
                    await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY)
            await runner.cleanup()

    async def _get_catchup_events_handler(self, request: web.Request) -> web.Response:
        try:
            min_event_message_seq = int(request.query['min_event_message_seq'])
            if min_event_message_seq == 0:
                catchup_events = self._event_message_cache.latest_event_messages(min_event_message_seq)
            else:
                last_event_message_seq = min_event_message_seq - 1
                last_event_message_hash = request.query['last_event_message_hash']
                # get the last event the client received as well so we can check its hash
                catchup_events = self._event_message_cache.latest_event_messages(last_event_message_seq)
                assert catchup_events != [], "Cache did not include the event_message for specified last_event_message_hash"
                last_event_message = catchup_events.pop(0)
                assert hash_bytes(last_event_message.serialize_to_bytes()) == last_event_message_hash, f"Invalid last_event_message_hash"
            # now continue
            response = web.StreamResponse(
                status=200,
                reason='OK',
                headers={'Content-Type': 'application/octet-stream'},
            )
            await response.prepare(request)
            for event in catchup_events:
                await response.write(event.serialize_to_bytes())
            await response.write_eof()

        except AssertionError as e:
            logger.error(f"AssertionError in {self.__class__.__name__}._get_catchup_events_handler() while attempting to retrieve cached event messages with min_event_message_seq={min_event_message_seq}: {e}")
            raise web.HTTPBadRequest() 
        except EventMessageCacheException as e:
            logger.error(f"EventMessageCacheException in {self.__class__.__name__}._get_catchup_events_handler() while attempting to retrieve cached event messages with mi_event_message_seq={min_event_message_seq}: {e}")
            raise web.HTTPBadRequest()            
        except KeyError as e:
            logger.error(f"Missing query field `{e}` in {self.__class__.__name__}._get_catchup_events_handler()")
            raise web.HTTPBadRequest()
        except ValueError:
            logger.error(f"Parsing error in {self.__class__.__name__}._get_catchup_events_handler(): {e}")
            raise web.HTTPBadRequest()
        except Exception as e:
            logger.error(f"Unexpected Exception in {self.__class__.__name__}._get_catchup_events_handler(): {e}")
            raise



    def _reserve_command_bus(self):
        if self.is_command_bus_reserved():
            raise ServiceBusException("command-bus is already reserved")
        else:
            self._is_command_bus_reserved = True

    def _unreserve_command_bus(self):
        self._is_command_bus_reserved = False


    async def _get_event_bus_handler(self, request: web.Request) -> web.Response:
        ws = web.WebSocketResponse( autoping=True,
                                    heartbeat=self.WEBSOCKET_HEARTBEAT,
                                    receive_timeout=self.WEBSOCKET_READ_TIMEOUT,
                                    max_msg_size=self.WEBSOCKET_MAX_MSG_SIZE )
        await ws.prepare(request)
        request.app['websockets'].add(ws)
        try:
            await self._manage_event_bus_ws(ws, self._event_message_pub_sub)
        except Exception as e:
            logger.error(f"Closing event-bus due to exception: {e}")
        finally:
            request.app['websockets'].discard(ws)



    async def _get_command_bus_handler(self, request: web.Request) -> web.Response:
        if self.is_command_bus_reserved():
            logger.error(f"command-bus is already reserved, closing the socket.")
            raise web.HTTPServiceUnavailable()
        # otherwise
        self._reserve_command_bus()
        ws = web.WebSocketResponse( autoping=True,
                                    heartbeat=self.WEBSOCKET_HEARTBEAT,
                                    receive_timeout=self.WEBSOCKET_READ_TIMEOUT,
                                    max_msg_size=self.WEBSOCKET_MAX_MSG_SIZE )
        await ws.prepare(request)
        request.app['websockets'].add(ws)
        try:
            await self._manage_command_bus_ws(ws, self._command_message_queue, self._command_receipt_message_queue, self._command_bus_cache)
        except Exception as e:
            logger.error(f"Closing command-bus due to exception: {e}")
        finally:
            self._unreserve_command_bus()
            request.app['websockets'].discard(ws)



    async def receive_command_message(self):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke receive_command_message() on a {self.__class__.__name__} that is not active")
        return await self._command_message_queue.get()

    async def send_command_receipt_message(self, command_receipt_message: service_bus_messages.CommandReceiptMessage):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke send_command_receipt_message() on a {self.__class__.__name__} that is not active")
        await self._command_receipt_message_queue.put(command_receipt_message)

    async def send_event_message(self, event_message: service_bus_messages.EventMessage):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke send_event_message() on a {self.__class__.__name__} that is not active")
        elif self.next_event_message_seq() != event_message.seq():
            raise ServiceBusException(f"Invalid event_message seq number in {self.__class__.__name__}.send_event_message(). Expected {self.next_event_message_seq()} not {event_message.seq()}")
        self._next_event_message_seq += 1
        self._event_message_cache.add(event_message)
        await self._event_message_pub_sub.publish(event_message)

    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        tasks = [
            asyncio.create_task(self._run_server()),
        ]
        self._task_runner = AsyncTaskRunner(tasks)
        await self._task_runner.start()

    async def run(self):
        await self.start()
        await self.wait_closed()

    async def wait_closed(self):
        if self._task_runner:
            await self._task_runner.wait_closed()

    async def close(self):
        if self._task_runner:
            await self._task_runner.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        close_task = asyncio.create_task(self.close())
        try:
            await asyncio.shield(close_task)
        except asyncio.CancelledError:
            await close_task
            raise
        except Exception as e:
            logger.info(f"{self.__class__.__name__} is suppressing exception with type `{type(e)}` : {e}")



class _FatalServiceBusException(ServiceBusException):
    pass


class HttpServiceBusClient(ServiceBusClient):
    RECONNECTION_ATTEMPTS = 5
    RECONNECTION_ATTEMPT_RESET_THRESHOLD_MS = 500
    FAILED_RECONNECTION_SLEEP_MS = 500
    CLIENT_CONNECT_TIMEOUT = 5
    CLIENT_READ_TIMEOUT = 5
    WEBSOCKET_HEARTBEAT = 1


    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._event_message_queue = AsyncQueue()
        self._last_event_message = None
        self._task_runner = None

    def host(self):
        return self._host

    def port(self):
        return self._port

    def has_last_event_message(self):
        return (self._last_event_message is not None)

    def last_event_message(self):
        if (not self.has_last_event_message()):
            raise ServiceBusException(f"Cannot return last_event_message when one does not exist !")
        return self._last_event_message

    def next_event_message_seq(self):
        if self.has_last_event_message():
            return self.last_event_message().seq() + 1
        else:
            return 0

    @classmethod
    def catchup_events_url(cls, host: str, port: int):
        return f"http://{host}:{port}/catchup-event-messages"

    @classmethod
    def event_bus_url(cls, host: str, port: int):
        return f"ws://{host}:{port}/event-bus"


    @classmethod
    async def _generate_ws_connection(cls, session: aiohttp.ClientSession, ws_url: str):
        try:
            reconnection_attempts = 1
            while reconnection_attempts <= cls.RECONNECTION_ATTEMPTS:
                logger.info(f"Attempt #{reconnection_attempts} to connect to websocket at `{ws_url}`")
                last_connection_attempt_timestamp = system_timestamp()
                try:
                    async with session.ws_connect(url=ws_url, heartbeat=cls.WEBSOCKET_HEARTBEAT, autoping=True) as ws:
                        yield ws
                except ServiceBusException as e:
                    logger.error(f"Exception in {cls.__name__}._generate_ws_connection(): {e}")
                except Exception as e:
                    logger.error(f"Connection to web-socket at `{ws_url} was lost")
                # reset the reconnection threshold if the connection stayed open for a while
                if system_timestamp() > last_connection_attempt_timestamp + cls.RECONNECTION_ATTEMPT_RESET_THRESHOLD_MS:
                    reconnection_attempts = 1
                else:
                    reconnection_attempts += 1
                    await asyncio.sleep(cls.FAILED_RECONNECTION_SLEEP_MS/1000)
            logger.error(f"Failed after {cls.RECONNECTION_ATTEMPTS} attempts to connect to {ws_url}")
        except Exception as e:
            logger.error(f"Unexpected exception in {cls.__name__}._generate_ws_connection(): {e}")
            raise

    @classmethod
    async def _request_catchup_event_messages(cls, session: aiohttp.ClientSession, catchup_events_url: str, min_event_message_seq: int, last_event_message_hash: str = ''):
        try:
            request_params = {
                'min_event_message_seq': min_event_message_seq
            }
            if last_event_message_hash:
                request_params['last_event_message_hash'] = last_event_message_hash
            async with session.get(catchup_events_url, params=request_params) as resp:
                assert resp.status == 200, f"Expected HTTP status code 200 not {resp.status}"
                buf = io.BytesIO()
                buf.write(await resp.read())
                buf.seek(0)
                return list(service_bus_messages.EventMessage.generate_from_stream(buf))
        except AssertionError as e:
            raise _FatalServiceBusException(f"{cls.__name__}._request_catchup_event_messages() failed because of AssertionError: {e}")
        except aiohttp.ClientResponseError as e:
            raise _FatalServiceBusException(f"{cls.__name__}._request_catchup_event_messages() failed because of a communication error: {e}")
        except ValueError as e:
            raise _FatalServiceBusException(f"{cls.__name__}._request_catchup_event_messages() failed because it failed to parse the event messages returned")


    async def _manage_event_bus_ws(self, session: aiohttp.ClientSession, ws: web.WebSocketResponse,
                                        catchup_events_url: str, event_message_queue: AsyncQueue):
        async with WSManager(ws) as ws_manager:
            logger.info(f"Established event-bus websocket in {self.__class__.__name__}._manage_event_bus_ws()")

            
            # calculate the last event message hash
            last_event_message_hash = hash_bytes(self.last_event_message().serialize_to_bytes()) if self.has_last_event_message() else ''
            catchup_event_messages = await self._request_catchup_event_messages(    session,
                                                                                    catchup_events_url,
                                                                                    self.next_event_message_seq(),
                                                                                    last_event_message_hash  )
            logger.debug(f"Requested catchup event messages. Found {len(catchup_event_messages)}")           
            # the expected seq number is from where we last left off
            min_event_message_seq = self.next_event_message_seq()
            # produce the catchup messages
            for event_message in catchup_event_messages:
                if event_message.seq() != min_event_message_seq:
                    raise ServiceBusException(f"Expected catchup event_message seq number {min_event_message_seq} not {event_message.seq()} in {self.__class__.__name__}._manage_event_bus_ws()")
                await event_message_queue.put(event_message)
                min_event_message_seq = event_message.seq() + 1
                # record last event message received
                self._last_event_message = event_message
            # now we have caught up, lets get the live event messages now
            while (not ws_manager.is_closed()):
                event_message = service_bus_messages.EventMessage.create_from_bytes(await ws_manager.receive_bytes())
                if event_message.seq() >= min_event_message_seq:
                    # enforce sequence numbers
                    if event_message.seq() != self.next_event_message_seq():
                        raise ServiceBusException(f"Expected event_message seq number {self.next_event_message_seq()} not {event_message.seq()} in {self.__class__.__name__}._manage_event_bus_ws()")
                    # tell our customer
                    await event_message_queue.put(event_message)
                    # record last event message received
                    self._last_event_message = event_message


    async def _manage_event_bus(self, session: aiohttp.ClientSession, host: str, port: int, event_message_queue: AsyncQueue):
        event_bus_url = self.event_bus_url(host, port)
        catchup_events_url = self.catchup_events_url(host, port)
        # Keep trying to maintain a resilient websocket connection
        async for ws in self._generate_ws_connection(session, event_bus_url):
            try:
                await self._manage_event_bus_ws(session, ws, catchup_events_url, event_message_queue)
            except _FatalServiceBusException as e:
                raise
            except ServiceBusException as e:
                logger.error(f"{self.__class__.__name__}._manage_event_bus() will re-connect due to ServiceBusException: {e}")
            except Exception as e:
                logger.error(f"Unexpected exception `{type(e)}` in {self.__class__.__name__}._manage_event_bus(): {e}")
                raise


    async def _manage_client_session(self):
        try:
            timeout = aiohttp.ClientTimeout(total=None,
                                            connect=self.CLIENT_CONNECT_TIMEOUT,
                                            sock_connect=self.CLIENT_CONNECT_TIMEOUT,
                                            sock_read=self.CLIENT_READ_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                await self._manage_event_bus(session, self.host(), self.port(), self._event_message_queue)
        except _FatalServiceBusException as e:
            logger.error(f"{self.__class__.__name__}._manage_client_session() is quitting due to fatal exception: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected exception in {self.__class__.__name__}._manage_client_session(): {e}")
            raise
        finally:
            logger.debug(f"Exiting {self.__class__.__name__}._manage_client_session()")

    async def receive_event_message(self):
        task = asyncio.create_task(self._event_message_queue.get())
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.done():
                raise ServiceBusException(f"Could not return an event_message from {self.__class__.__name__}.receive_event_message() because it is closing.")
            else:
                await AsyncTaskHelper.cancel_and_wait(task)
                raise

    async def send_command_message(self, command_message: service_bus_messages.CommandMessage):
        raise ServiceBusException(f"Cannot send a command message from {self.__class__.__name__}")

    async def receive_command_receipt_message(self):
        raise ServiceBusException(f"Cannot receive a command_receipt_message in {self.__class__.__name__}")

    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        tasks = [
            asyncio.create_task(self._manage_client_session())
        ]
        self._task_runner = AsyncTaskRunner(tasks)
        await self._task_runner.start()

    async def run(self):
        await self.start()
        await self.wait_closed()

    async def wait_closed(self):
        if self._task_runner:
            await self._task_runner.wait_closed()

    async def close(self):
        if self._task_runner:
            await self._task_runner.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        close_task = asyncio.create_task(self.close())
        try:
            await asyncio.shield(close_task)
        except asyncio.CancelledError:
            await close_task
            raise
        except Exception as e:
            logger.info(f"{self.__class__.__name__} is suppressing exception with type `{type(e)}` : {e}")




class HttpCommandableServiceBusClient(HttpServiceBusClient):
    COMMAND_RECEIPT_MESSAGE_TIMEOUT = 3

    def __init__(self, host: str, port: int):
        super().__init__(host, port)
        self._command_message_queue = AsyncQueue()
        self._command_receipt_message_queue = AsyncQueue()
        self._command_message_in_flight = None

    @classmethod
    def command_bus_url(cls, host: str, port: int):
        return f"ws://{host}:{port}/command-bus"


    @classmethod
    async def _send_and_receive(cls, ws_manager: WSManager, send_bytes: bytes):
        try:
            await ws_manager.send_bytes(send_bytes)
            receive_bytes_task = asyncio.create_task(ws_manager.receive_bytes())
            result = await AsyncTaskHelper.wait_for_all_and_cancel_pending( [receive_bytes_task],
                                                                            timeout=cls.COMMAND_RECEIPT_MESSAGE_TIMEOUT )
            return result[0]
        except asyncio.TimeoutError:
            raise ServiceBusException(f"Timeout while waiting for command_receipt_message in {cls.__name__}._manage_command_bus_ws()")
        except ServiceBusException as e:
            raise ServiceBusException(f"{cls.__name__}._send_and_receive() failed")


    async def _manage_command_bus_ws(   self, ws: web.WebSocketResponse, command_message_queue: AsyncQueue,
                                        command_receipt_message_queue: AsyncQueue  ):
        async with WSManager(ws) as ws_manager:
            logger.info(f"Established command-bus websocket in {self.__class__.__name__}._manage_command_bus_ws()")
            if self._command_message_in_flight:
                logger.info(f"Left-over command_message {self._command_message_in_flight} in {self.__class__.__name__}._manage_command_bus_ws()")

            while (not ws_manager.is_closed()):
                # need to wait for a command from customer
                while (not self._command_message_in_flight):
                    self._command_message_in_flight = await command_message_queue.get()
                # send-recv
                received_bytes = await self._send_and_receive(ws_manager, self._command_message_in_flight.serialize_to_bytes())
                # we got a receipt !
                try:
                    command_receipt_message = service_bus_messages.CommandReceiptMessage.create_from_bytes(received_bytes)
                    # inform customer
                    await command_receipt_message_queue.put(command_receipt_message)
                    # reset for next command
                    self._command_message_in_flight = None
                except ValueError:
                    raise ServiceBusException(f"Received invalid command_receipt_message in {self.__class__.__name__}._manage_command_bus_ws()")




    async def _manage_command_bus(self, session: aiohttp.ClientSession, host: str, port: int,
                                        command_message_queue: AsyncQueue, command_receipt_message_queue: AsyncQueue):
        command_bus_url = self.command_bus_url(host, port)
        # Keep trying to maintain a resilient websocket connection
        async for ws in self._generate_ws_connection(session, command_bus_url):
            try:
                await self._manage_command_bus_ws(ws, command_message_queue, command_receipt_message_queue)
            except ServiceBusException as e:
                logger.error(f"ServiceBusException in {self.__class__.__name__}._manage_command_bus(): {e}")
            except Exception as e:
                logger.error(f"Unexpected exception `{type(e)}` in {self.__class__.__name__}._manage_command_bus(): {e}")
                raise


    async def _manage_client_session(self):
        try:
            timeout = aiohttp.ClientTimeout(total=None,
                                            connect=self.CLIENT_CONNECT_TIMEOUT,
                                            sock_connect=self.CLIENT_CONNECT_TIMEOUT,
                                            sock_read=self.CLIENT_READ_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                tasks = [
                    asyncio.create_task(self._manage_event_bus( session,
                                                                self.host(),
                                                                self.port(),
                                                                self._event_message_queue )),
                    asyncio.create_task(self._manage_command_bus(   session,
                                                                    self.host(),
                                                                    self.port(),
                                                                    self._command_message_queue,
                                                                    self._command_receipt_message_queue  ))
                ]
                async with AsyncTaskRunner(tasks) as task_runner:
                    await task_runner.wait_closed()
        except Exception as e:
            logger.error(f"Unexpected exception in {self.__class__.__name__}._manage_client_session(): {e}")
            raise
        finally:
            logger.debug(f"Exiting {self.__class__.__name__}._manage_client_session()")


    async def send_command_message(self, command_message: service_bus_messages.CommandMessage):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke send_command_message() on a {self.__class__.__name__} that is not active")
        await self._command_message_queue.put(command_message)


    async def receive_command_receipt_message(self):
        task = asyncio.create_task(self._command_receipt_message_queue.get())
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.done():
                raise ServiceBusException(f"Could not return a command_receipt_message from {self.__class__.__name__}.receive_command_receipt_message() because it is closing.")
            else:
                await AsyncTaskHelper.cancel_and_wait(task)
                raise
