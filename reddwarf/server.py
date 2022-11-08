import json
from typing import Awaitable, Callable, Union, List, Any
from importlib import import_module
from inspect import iscoroutinefunction, isfunction, getmembers
from os import walk
from functools import reduce
from operator import add

import pydantic
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.routing import Route, WebSocketRoute, BaseRoute
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket
from starlette_context import plugins
from starlette_context.middleware import ContextMiddleware
from starlette_context import ctx
from utils.auth import authenticate_token, create_token


APP_SECRET = 'SECRET'


class CallRegisterException(Exception):
    pass


class ShitParam(pydantic.BaseModel):
    count: int


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        match Request(scope).headers.get('authorization').split(" "):
            case "Bearer", bearer_token:
                user = authenticate_token(
                    bearer_token,
                    APP_SECRET
                )
                for k, v in user.items():
                    ctx.context.setdefault(k, v)
                await self.app(scope, receive, send)
            case _:
                res = JSONResponse({"auth": "invalid"})
                await res(scope, receive, send)
                return


class InvalidCredential(BaseException):
    """when u are not authenticated"""


class BaseWebsocketHandler(WebSocketEndpoint):
    encoding: 'json'

    def __init__(self, scope, receive, send) -> None:
        super().__init__(scope, receive, send)
        self.authenticated = False
        self.user: dict = {}

    async def on_connect(self, websocket: WebSocket):
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: Any) -> None:
        print(self.authenticated)
        if not self.authenticated:
            # try:
            print(data)
            auth_data = json.loads(data.strip())
            print(auth_data)
            try:
                match auth_data:
                    case {"token": str(token)}:
                        print(f"token -> {token}")
                        auth_user = authenticate_token(token, APP_SECRET)
                        if auth_user is None:
                            raise InvalidCredential
                        self.authenticated = True
                        self.user = auth_user
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


def rpc_wrapper(func, param_class: pydantic.BaseModel):
    try:
        assert iscoroutinefunction(func)
    except AssertionError:
        raise CallRegisterException(f"{func} is not an awaitable coroutine function!")

    async def execute(request):
        params = param_class(**await request.json()) if await request.body() != b'' else None

        if params is None:
            return JSONResponse(await func())
        if not isinstance(params, param_class):
            return JSONResponse({
                "error": f"{type(params)} is not {param_class.__name__} {param_class.schema_json()}"
            })
        return JSONResponse(await func(params))
        # return JSONResponse(await func(**params))

    return execute


def create_route_for_rpc(func, param_class) -> Route:
    api_prefix = '/rpc'
    return Route('/'.join([api_prefix, func.__name__]), rpc_wrapper(func, param_class), methods=['POST'])


def create_route_for_websocket(handler) -> WebSocketRoute:
    api_prefix = '/ws'
    return WebSocketRoute('/'.join([api_prefix, handler.get_endpoint()]), handler)


def test_token():
    print(create_token({"username": "noctoid", "uid": 100}, APP_SECRET))

def get_app(
        config=None,
        routes: list[tuple, Union[Awaitable, Callable]] = None,
        ws_routes: list[BaseWebsocketHandler] = None,
) -> Starlette:
    """
    :param config:
        A Dict with customized config
    :param routes: 
        A list of functions to be registered as RPCs
    :param ws_routes:
        A list of WenSocketHandlers to be registered as WS routes
    :return:
        A Starlette app loaded with RPCs
    """
    sources = []
    if config is None:
        config = {}
    for (root, dir_, filenames) in walk(config.get("root", "rpc")):
        parent_module_name = ".".join(root.split("/"))
        for filename in filenames:
            if filename.endswith(".py"):
                module_name, _ = filename.split(".")
                sources.append(".".join([parent_module_name, module_name]))

    if routes is None:
        routes = reduce(add, ([i[1] for i in getmembers(import_module(source), isfunction)] for source in sources))
    return Starlette(
        routes=[
            create_route_for_rpc(func, param_class) for func, param_class in routes
        ] + [
            create_route_for_websocket(handler) for handler in ws_routes
        ],
        middleware=[
            Middleware(
                ContextMiddleware,
                plugins=(
                    plugins.RequestIdPlugin(),
                    plugins.CorrelationIdPlugin(),
                )
            ),
            Middleware(AuthMiddleware),
        ],
        on_startup=[test_token],
    )
