from datetime import datetime
from asyncio import sleep
from pydantic import BaseModel, ValidationError, validator
from starlette.websockets import WebSocket
from server import WebSocketEndpoint, get_app

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
    print(type(foobar2param))
    print(type(foobar2param.trading_day), foobar2param.trading_day)
    for i in foobar2param.account_id:
        print(type(i), i)
    return {
        'message': f"requesting data of {foobar2param.trading_day}"
                   f"and {foobar2param.account_id}"
    }

class asyncrange:

    class __asyncrange:
        def __init__(self, *args):
            self.__iter_range = iter(range(*args))

        async def __anext__(self):
            try:
                return next(self.__iter_range)           
            except StopIteration as e:
                raise StopAsyncIteration(str(e))

    def __init__(self, *args):
        self.__args = args

    def __aiter__(self):
        return self.__asyncrange(*self.__args)

class FoobarStream(WebSocketEndpoint):
    encoding: 'bytes'
    endpoint = 'foobar_stream'

    async def on_connect(self, ws):
        await ws.accept()
        print("new client connected")

    async def on_receive(self, ws: WebSocket, data):
        if data.strip() in ('START', 'ACK'):
            await sleep(3)    
            print(f'sending segment piece')
            await ws.send_json({"segment": 'segment piece'})
        elif data.strip() in ('EXIT'):
            ws.close(code=0, reason=None)
                
        print(f"received: {data}")
        await ws.send_json({"echo": data})

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        print("client disconnected")
        await websocket.close(code=0, reason=None)

app = get_app(
    config=None,
    routes=[(foobar, None), (foobar2, Foobar2Param)],
    ws_routes=[FoobarStream]
)
    
