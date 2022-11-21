from jwt.exceptions import InvalidSignatureError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette_context import ctx

# from reddwarf.server import APP_SECRET
from reddwarf.utils.auth import authenticate_token


class AuthMiddleware:
    def __init__(self, app, no_auth_routes=None):
        self.app = app
        self.no_auth_routes = no_auth_routes if no_auth_routes else []

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        if request.url.path in self.no_auth_routes:
            await self.app(scope, receive, send)
            return

        auth_header = request.headers.get('authorization')
        if not auth_header:
            res = JSONResponse({"auth": "invalid"})
            await res(scope, receive, send)
            return

        match auth_header.split(" "):
            case "Bearer", bearer_token:
                try:
                    user = authenticate_token(bearer_token)
                except InvalidSignatureError:
                    response = JSONResponse({"auth": "invalid"}, status_code=403)
                    await response(scope, receive, send)
                    return
                if user is None:
                    response = JSONResponse({"auth": "invalid"}, status_code=403)
                    await response(scope, receive, send)
                    return
                for k, v in user.items():
                    ctx.context.setdefault(k, v)
                await self.app(scope, receive, send)
            case _:
                res = JSONResponse({"auth": "invalid"})
                await res(scope, receive, send)
                return
