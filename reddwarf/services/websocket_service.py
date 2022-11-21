from starlette.websockets import WebSocket
from reddwarf.utils.context import get_current_user


def get_connection(endpoint):
    connection_manager = WSConnectionManager()
    return connection_manager.get_connection(f"{get_current_user()}::{endpoint.get_endpoint()}")


class WSConnectionManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(WSConnectionManager, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        pass

    def initialize(self, max_clients=10000):
        self._connections: dict[str, WebSocket] = {}

    def get_connection(self, connection_id: str) -> WebSocket | None:
        return self._connections.get(connection_id)

    def get_all_connections(self) -> list[WebSocket]:
        return list(self._connections.values())

    def register_connection(self, connection_id: str, new_connection: WebSocket):
        self._connections[connection_id] = new_connection

    def unregister_connection(self, connection_id) -> WebSocket:
        return self._connections.pop(connection_id)
