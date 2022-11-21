import json
from typing import Any
from uuid import uuid4

from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket

from reddwarf.exceptions import InvalidCredential
from reddwarf.utils.auth import authenticate_token

from reddwarf.services.websocket_service import WSConnectionManager


connection_manager = WSConnectionManager()


class BaseWebsocketHandler(WebSocketEndpoint):
    encoding: 'json'

    def __init__(self, scope, receive, send) -> None:
        super().__init__(scope, receive, send)
        self.authenticated = False
        self.user: dict = {}

    @staticmethod
    def get_endpoint():
        raise NotImplementedError()

    async def on_connect(self, websocket: WebSocket):
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: Any) -> None:
        if not self.authenticated:
            # try:
            print(data)
            auth_data = json.loads(data.strip())
            print(auth_data)
            try:
                match auth_data:
                    case {"token": str(token)}:
                        print(f"token -> {token}")
                        auth_user = authenticate_token(token)
                        if auth_user is None:
                            raise InvalidCredential
                        self.authenticated = True
                        self.user = auth_user
                        connection_manager.register_connection(
                            f"{auth_user['username']}::{self.get_endpoint()}", websocket
                        )
                        print(connection_manager.get_all_connections())
                        await websocket.send_json({"status": "success"})
                        return
                    case _:
                        raise InvalidCredential

            except (json.decoder.JSONDecodeError, InvalidCredential):
                await websocket.send_json({"error": "not authenticated"})
                print('no auth')
                return
        print("auth success")
        await websocket.send_json(await self.handle_received_message(data))

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        print("client disconnected")
        await websocket.close(code=0, reason=None)

    async def handle_received_message(self, data: Any):
        raise NotImplementedError()
