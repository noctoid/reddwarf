from typing import Awaitable, Callable, Union, List
from importlib import import_module
from inspect import iscoroutinefunction, isfunction, getmembers
from os import walk
from functools import reduce
from operator import add

import pydantic
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.responses import JSONResponse
from starlette.endpoints import WebSocketEndpoint


class CallRegisterException(Exception):
    pass

class ShitParam(pydantic.BaseModel):
    count: int

def rpc_wrapper(func, param_class: pydantic.BaseModel):
    try:
        assert iscoroutinefunction(func)
    except AssertionError:
        raise CallRegisterException(f"{func} is not an awaitable coroutine function!")

    async def execute(request):
        # print(request.__dict__)
        # print(await request.body(), type(await request.body()))
        params = param_class(**await request.json()) if await request.body() != b'' else None
        # params = await request.json()
        # params = ShitParam(**params)
        
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

def create_route_for_websocket(handler: WebSocketEndpoint) -> WebSocketRoute:
    api_prefix = '/ws'
    return WebSocketRoute('/'.join([api_prefix, getattr(handler, 'endpoint') or handler.__name__]), handler)

def get_app(
        config=None, 
        routes: List[Union[Awaitable, Callable]] = None, 
        ws_routes: List[WebSocketEndpoint]=None,
) -> Starlette:
    """
    :param config:
        A Dict with customized config
    :param routes: 
        A list of functions to be registered as RPCs 
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
        ]+[
            create_route_for_websocket(handler) for handler in ws_routes
        ]
    )
