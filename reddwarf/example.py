from asyncio import sleep
from starlette.websockets import WebSocket
from starlette.applications import Starlette

from starlette.routing import Route, Mount, WebSocketRoute

http_endpoints = [
    
]

async def produce_delayed_result(t, msg=None):
    await sleep(t)
    return msg or "this is a test ws text"

async def example_ws(ws):
    # ws = WebSocket(scope, receive, send)
    await ws.accept()
    while 1:
        # received_command = await ws.receive_text()
        await ws.send_text(await produce_delayed_result(2, received_command))
    await ws.close()

routes = [
    WebSocketRoute('/test', example_ws),
]

def startup():
    print("Ah shit, here we go again.")

app = Starlette(debug=True, routes=routes, on_startup=[startup])

@app.websocket_route('/ws')
async def ws(ws):
    # ws = WebSocket(scope, receive, send)
    await ws.accept()
    await ws.send_text(await produce_delayed_result(2))
    await ws.close()
