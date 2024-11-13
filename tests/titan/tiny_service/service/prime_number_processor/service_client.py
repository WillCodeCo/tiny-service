from titan.tiny_service import service
from tests.titan.tiny_service.service.prime_number_processor import service_interface

class ServiceClient(service.ServiceClient):

    @classmethod
    def deserialize_event(cls, event_type: str, event_bytes: bytes):
        if event_type == service_interface.FoundPrimeSquareEvent.event_type():
            return service_interface.FoundPrimeSquareEvent.create_from_bytes(event_bytes)
        else:
            raise service.UnrecognizedEventException(f"Event `{event_type}` not recognized")



