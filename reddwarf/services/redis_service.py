import aioredis


class RedisConnection:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(RedisConnection, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        pass

    async def initialize(self, host, port=None, username=None, password=None):
        self._connection = await aioredis.from_url(
            f'redis://{host}{":"+str(port) if port else ""}',
            username=username, password=password, decode_responses=True,
        )

    def get_pool(self):
        return self._connection.client()
