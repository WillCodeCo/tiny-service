import asyncio
import logging
from titan.tiny_service.async_helper import AsyncTaskRunner, AsyncTaskHelper, AsyncQueue
from titan.tiny_service import events
from titan.tiny_service import commands
from titan.tiny_service.service.service_bus import (
    service_bus_messages,
    ServiceBusException,
    ServiceBusClient
)
from titan.tiny_service.service.command_receipt import (
    CommandReceipt,
    CommandAcceptedReceipt,
    CommandRejectedReceipt,
    InvalidCommandReceipt
)


logger = logging.getLogger(__name__)


class ServiceClientException(Exception):
    pass

class UnrecognizedEventException(ServiceClientException):
    pass

class UnrecognizedCommandReceiptException(ServiceClientException):
    pass


class ServiceClient(events.EventProducer, commands.CommandExecutor):
    def __init__(self, service_bus_client: ServiceBusClient):
        self._service_bus_client = service_bus_client

    @classmethod
    def deserialize_event(cls, event_type: str, event_bytes: bytes):
        raise UnrecognizedEventException("ServiceClient.deserialize_event() method has not been implemented !")

    @classmethod
    def deserialize_command_receipt(cls, command_receipt_type: str, command_receipt_bytes: bytes):
        if command_receipt_type == "CommandAcceptedReceipt":
            return CommandAcceptedReceipt.create_from_bytes(command_receipt_bytes)
        elif command_receipt_type == "InvalidCommandReceipt":
            return InvalidCommandReceipt.create_from_bytes(command_receipt_bytes)
        elif command_receipt_type == "CommandRejectedReceipt":
            return CommandRejectedReceipt.create_from_bytes(command_receipt_bytes)
        else:
            raise UnrecognizedCommandReceiptException(f"CommandReceipt `{command_receipt_type}` not recognized")

    def service_bus_client(self):
        return self._service_bus_client

    def active(self):
        return (self._service_bus_client.active())

    async def receive_event(self):
        if (not self.active()):
            raise events.EventProducerException(f"Could not receive_event() when ServiceClient is not active.")
        receive_task = asyncio.create_task(self._service_bus_client.receive_event_message())
        try:
            event_message = await asyncio.shield(receive_task)
            return self.deserialize_event(event_message.event_type(), event_message.event_bytes())
        except asyncio.CancelledError:
            # Distinguish between the caller cancelling
            if receive_task.cancelled():
                raise events.EventProducerException(f"Failed to receive_event() because ServiceClient was cancelled.")
            else:
                await AsyncTaskHelper.cancel_all_and_ignore_exceptions([receive_task])
                raise asyncio.CancelledError
        except UnrecognizedEventException as e:
            raise events.EventProducerException(f"Failed to receive_event() : {e}")
        except Exception as e:
            raise events.EventProducerException(f"Failed to receive_event() because of unexpected exception: {e}")



    async def execute_command(self, command: commands.Command):
        if (not self.active()):
            raise commands.CommandExecutorException(f"Could not execute_command() when ServiceClient is not active.")
        try:

            command_message = service_bus_messages.CommandMessage(  command_type=command.command_type(),
                                                                    command_bytes=command.serialize_to_bytes()  )
            await self._service_bus_client.send_command_message(command_message)

            command_receipt_message = await self._service_bus_client.receive_command_receipt_message()
            command_receipt = ServiceClient.deserialize_command_receipt(command_receipt_message.command_receipt_type(),
                                                                        command_receipt_message.command_receipt_bytes())
            
            assert (not isinstance(command_receipt, InvalidCommandReceipt)), f"The service considered the command `{command.command_id()}` as 'invalid'`"
            assert (not isinstance(command_receipt, CommandRejectedReceipt)), f"The service rejected the command with an error `{command_receipt.reason()}`"

            return
        except ValueError:
            raise commands.CommandExecutorException(f"Failed to deserialize command receipt for command `{command.command_id()}` : {e}")
        except UnrecognizedCommandReceiptException as e:
            raise commands.CommandExecutorException(f"Received an unrecognized command receipt for command `{command.command_id()}` : {e}")
        except AssertionError as e:
            raise commands.CommandExecutorException(f"Failed to execute command `{command.command_id()}`: {e.args[0]}")
        except asyncio.CancelledError:
            raise commands.CommandExecutorException(f"Failed to execute command `{command.command_id()}` because ServiceClient was cancelled.")
        except Exception as e:
            logger.error(f"Unexpected exception in ServiceClient.execute_command(): {e}")
            raise

