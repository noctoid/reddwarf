import traceback
import uvloop
from typing import Awaitable, Callable, Union
from inspect import iscoroutinefunction, get_annotations

import pydantic
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Route, WebSocketRoute, BaseRoute, Mount
from starlette.responses import JSONResponse
from starlette_context import plugins
from starlette_context.middleware import ContextMiddleware
from hypercorn.config import Config
from hypercorn.asyncio import serve

from reddwarf.endpoints.websocket_endpoint import BaseWebsocketHandler
from reddwarf.exceptions import CallRegisterException
from reddwarf.middlewares import AuthMiddleware
from reddwarf.services.logger_service import BaseLogger
from reddwarf.services.websocket_service import WSConnectionManager
from reddwarf.services.config_service import BaseConfig
from reddwarf.services.mysql_service import MySQLPool
from reddwarf.services.redis_service import RedisConnection


class RedDwarf:
    def __init__(self, routes=None, ws_routes=None, no_auth_routes=None, loop=None):
        if loop is None:
            self._loop = uvloop.new_event_loop()
        else:
            self._loop = loop
        self._config = BaseConfig()
        self._config.load_conf()
        self._host_ip = self._config.get_config()['DEFAULT']['host']
        self._port = self._config.get_config()['DEFAULT']['port']
        self._ws_prefix = self._config.get_config()['DEFAULT']['ws_prefix']
        self._rpc_prefix = self._config.get_config()['DEFAULT']['rpc_prefix']
        self._logger = BaseLogger()
        self._logger.setup_logger(self._config.get_config()['DEFAULT']['log_file'])
        self._logger.log(level=10, msg="[INFO] Initializing Red Dwarf RPC Services...")
        self._app = self.get_app(routes=routes, ws_routes=ws_routes, no_auth_routes=no_auth_routes)
        self._logger.log(level=10, msg="[INFO] Initializing MySQL Connection Pool...")
        self._mysql_pool = MySQLPool()
        self._loop.run_until_complete(self._mysql_pool.create_mysql_pool(
            host=self._config.get_config()['MySQL']['db_host'],
            port=self._config.get_config()['MySQL']['db_port'],
            user=self._config.get_config()['MySQL']['db_user'],
            password=self._config.get_config()['MySQL']['db_password'],
            db=self._config.get_config()['MySQL']['db_name'],
            loop=loop
        ))
        self._logger.log(level=10, msg="[INFO] Initializing Redis Connection Pool...")
        self._redis_pool = RedisConnection()
        self._loop.run_until_complete(self._redis_pool.initialize(
            self._config.get_config()['Redis']['db_host'],
            password=self._config.get_config()['Redis']['db_password']
        ))
        self._logger.log(level=10, msg="[INFO] Initializing WebSocket Connection Manager...")
        self._ws_connection = WSConnectionManager()
        self._ws_connection.initialize()
        self._logger.log(
            level=10,
            msg=f'[INFO] Red Dwarf Started! Listening at {f"{self._host_ip}:{self._port}"}'
        )

    def init(self):
        config = Config()
        config.bind = [f"{self._host_ip}:{self._port}"]
        self._loop.run_until_complete(serve(self._app, config))
        self._mysql_pool.get_mysql_pool().close()
        self._loop.run_until_complete(self._mysql_pool.get_mysql_pool().wait_closed())

    def get_mysql_pool(self):
        return self._mysql_pool

    def get_logger(self):
        return self._logger

    def get_ws_connection_manager(self):
        return self._ws_connection

    def create_route_for_websocket(self, handler) -> BaseRoute:
        return WebSocketRoute(
            '/'.join([self._ws_prefix, handler.get_endpoint()]),
            handler
        )

    def create_route_for_rpc(self, func) -> Route:
        return Route(
            '/'.join([self._rpc_prefix, func.__name__]),
            self.rpc_wrapper(func), methods=['POST']
        )

    def rpc_wrapper(self, func):
        try:
            assert iscoroutinefunction(func)
        except AssertionError:
            raise CallRegisterException(f"{func} is not an awaitable coroutine function!")

        async def execute(request):
            params = get_annotations(func)
            if params and len(params) == 1:
                param_name, param_model = next(iter(params.items()))
                if issubclass(param_model, pydantic.BaseModel):
                    params = {param_name: param_model(**await request.json())}
            else:
                request_body = await request.json()
                params = {
                    param_name: request_body[param_name]
                    for param_name, param_type in params.items()
                    if request_body.get(param_name)
                }
                self._logger.log(level=10, msg=f'[INFO] extracting {params}')

            try:
                self._logger.log(level=10, msg=f'[INFO] calling {func.__name__} {params}')
                if not params:
                    return JSONResponse(await func())
                return JSONResponse(await func(**params))
            except Exception as e:
                self._logger.log(level=50, msg='str(e)', exc_info=traceback.format_exc())

        print(f"binding {func.__name__} {get_annotations(func)}")

        return execute

    def get_app(
            self,
            config=None,
            routes: list[tuple, Union[Awaitable, Callable]] = None,
            ws_routes: list[BaseWebsocketHandler] = None,
            no_auth_routes: list[tuple, Union[Awaitable, Callable]] = None,
    ) -> Starlette:
        """
        :param config:
            A Dict with customized config
        :param routes:
            A list of functions to be registered as RPCs
        :param ws_routes:
            A list of WenSocketHandlers to be registered as WS routes
        :starting_sequence:
            callbacks
        :ending_sequence:
            callbacks
        :return:
            A Starlette app loaded with RPCs
        """
        # sources = []
        if config is None:
            config = {}
        rpc_routes = [self.create_route_for_rpc(func) for func in routes]
        ws_routes = [self.create_route_for_websocket(handler) for handler in ws_routes]
        no_auth_routes = [self.create_route_for_rpc(func) for func in no_auth_routes]
        return Starlette(
            debug=True,
            routes=no_auth_routes+rpc_routes+ws_routes,
            middleware=[
                Middleware(
                    ContextMiddleware,
                    plugins=(
                        plugins.RequestIdPlugin(),
                        plugins.CorrelationIdPlugin(),
                    )
                ),
                Middleware(AuthMiddleware, no_auth_routes=[f.path for f in no_auth_routes]),
            ],
        )
