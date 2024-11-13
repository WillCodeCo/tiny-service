import asyncio
import logging
from titan.tiny_service.async_helper import AsyncTaskRunner, AsyncQueue
from titan.tiny_service import events
from titan.tiny_service import commands
from titan.tiny_service.service.service_bus import (
    service_bus_messages,
    ServiceBusException,
    ServiceBusServer
)
from titan.tiny_service.service import command_receipt

logger = logging.getLogger(__name__)


class ServiceException(Exception):
    pass

class UnrecognizedCommandException(ServiceException):
    pass

class InvalidCommandException(ServiceException):
    pass


class Service(commands.AsyncCommandExecutor):
    def __init__(self, service_bus_server: ServiceBusServer):
        self._service_bus_server = service_bus_server
        self._command_queue = AsyncQueue()
        self._service_task_runner = None
        self._event_seq = 0

    @classmethod
    def deserialize_command(cls, command_type: str, command_bytes: bytes):
        raise UnrecognizedCommandException("Service.deserialize_command() method has not been implemented !")

    async def _command_executor(self):
        while True:
            command = await self._command_queue.get()
            try:
                await self.execute_command(command)
            except commands.CommandExecutorException as e:
                logger.error(f"Failed to execute command `{command}` due to exception: {e}", exc_info=True)
                raise ServiceException(f"Failed to execute command: {e}")


    async def _incoming_command_monitor(self):
        while True:
            try:
                command_message = await self._service_bus_server.receive_command_message()
                try:                                    
                    command = self.deserialize_command(command_message.command_type(), command_message.command_bytes())
                    try:
                        self.ensure_command_is_valid(command)
                        # we delay execution to ensure that events always come after the command-receipt !
                        await self.send_command_receipt(command_receipt.CommandAcceptedReceipt(command.command_id()))                
                        await self._command_queue.put(command)
                    except InvalidCommandException as e:
                        await self.send_command_receipt(command_receipt.CommandRejectedReceipt(command.command_id(), str(e)))
                except ValueError as e:
                    await self.send_command_receipt(command_receipt.InvalidCommandReceipt(f"Failed to de-serialize command: {e}"))
                except UnrecognizedCommandException:
                    await self.send_command_receipt(command_receipt.InvalidCommandReceipt(f"Failed to de-serialize command."))
            except ServiceBusException as e:
                continue

    def service_bus_server(self):
        return self._service_bus_server

    def active(self):
        return (self._service_task_runner) and (self._service_task_runner.active())

    async def send_command_receipt(self, command_receipt: command_receipt.CommandReceipt):
        if not self.active():
            raise ServiceException("Cannot send_command_receipt() when Service is not active")
        command_receipt_message = service_bus_messages.CommandReceiptMessage(   command_receipt_type=command_receipt.tuple_type(),
                                                                                command_receipt_bytes=command_receipt.serialize_to_bytes()  )
        await self._service_bus_server.send_command_receipt_message(command_receipt_message)

    async def publish_event(self, event: events.Event):
        if not self.active():
            raise ServiceException("Cannot send_event() when Service is not active")
        event_message = service_bus_messages.EventMessage(seq=self._event_seq, event_type=event.event_type(), event_bytes=event.serialize_to_bytes() )
        self._event_seq += 1
        await self._service_bus_server.send_event_message(event_message)


    def ensure_command_is_valid(self, command: commands.Command):
        """This method should be overidden by the subclass"""
        raise InvalidCommandException("Command could not be validated, since the Service.ensure_command_is_valid() method has not been implemented.")

    async def execute_command(self, command: commands.Command):
        """This method should be overidden by the subclass"""
        raise NotImplementedError("Service.execute_command() method has not been implemented !")

    async def service_main(self):
        """This method should be overidden by the subclass"""
        await self.wait_closed()

    async def start(self):
        tasks = [
            asyncio.create_task(self._service_bus_server.wait_closed()),
            asyncio.create_task(self._incoming_command_monitor()),
            asyncio.create_task(self._command_executor()),
            asyncio.create_task(self.service_main())
        ]
        self._service_task_runner = AsyncTaskRunner(tasks)
        await self._service_task_runner.start()

    async def run(self):
        await self.start()
        await self.wait_closed()

    async def wait_closed(self):
        if self._service_task_runner:
            await self._service_task_runner.wait_closed()

    async def close(self):
        if self._service_task_runner:
            await self._service_task_runner.close()

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

