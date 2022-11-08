import json
from typing import Any
from datetime import datetime
from asyncio import sleep
from pydantic import BaseModel, ValidationError, validator
from starlette.websockets import WebSocket, WebSocketState
from server import WebSocketEndpoint, get_app, BaseWebsocketHandler

from starlette.exceptions import WebSocketException

from utils.context import get_current_user


async def foobar():
    return {"an api endpoint with no parameter"}


class Foobar2Param(BaseModel):
    trading_day: str
    account_id: list[int]

    @validator('trading_day')
    def trading_day_format(cls, v: str):
        if any([
            len(v) != 8,
            not v.isnumeric() and type(eval(v)) != int
        ]):
            raise ValueError('trading_day should follow the format of YYYYMMDD')
        try:
            datetime.strptime(v, '%Y%m%d')
        except:
            raise ValueError(f'trading_day {v} is not a valid value')
        return v


async def foobar2(foobar2param: Foobar2Param):
    print(get_current_user())
    print(type(foobar2param))
    print(type(foobar2param.trading_day), foobar2param.trading_day)
    for i in foobar2param.account_id:
        print(type(i), i)
    return {
        'message': f"requesting data of {foobar2param.trading_day}"
                   f"and {foobar2param.account_id}",
        "user": get_current_user(),
    }


class FoobarStream(BaseWebsocketHandler):
    @staticmethod
    def get_endpoint():
        return 'foobar_stream'

    async def handle_received_message(self, data: Any):
        return {'echo': data.strip(), 'user': self.user['username']}


app = get_app(
    config=None,
    routes=[(foobar, None), (foobar2, Foobar2Param)],
    ws_routes=[FoobarStream]
)
