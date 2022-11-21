from contextvars import Context
from starlette_context import ctx


def get_current_user():
    print(ctx.context.data)
    return ctx.context.data["username"]
