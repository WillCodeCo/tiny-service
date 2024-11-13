import asyncio
from math import sqrt
from itertools import count, islice
import logging
from titan.tiny_service import service
from tests.titan.tiny_service.service.prime_number_processor import service_interface

logger = logging.getLogger(__name__)



def is_prime(n):
    return n > 1 and all(n%i for i in islice(count(2), int(sqrt(n)-1)))


class Service(service.Service):

    @classmethod
    def deserialize_command(cls, command_type: str, command_bytes: bytes):
        """Return an appropriate service-specific command instance for the given generic_command"""
        if command_type == service_interface.ProcessThisPrimeNumberCommand.command_type():
            return service_interface.ProcessThisPrimeNumberCommand.create_from_bytes(command_bytes)
        else:
            raise service.UnrecognizedCommandException(f"Command `{command_type}` not recognized")


    def ensure_command_is_valid(self, command):
        """Raise an InvalidCommandException if the command cannot be executed"""
        if (not is_prime(command.some_number())):
            raise service.InvalidCommandException(f"{command.some_number()} is not a prime !")

    async def execute_command(self, command):
        """Execute a valid command"""
        logger.info(f"Received command: {command}")
        if isinstance(command, service_interface.ProcessThisPrimeNumberCommand):
            await self.publish_event(service_interface.FoundPrimeSquareEvent.create(command.some_number()*command.some_number()))

