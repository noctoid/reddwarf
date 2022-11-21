import aiomysql

from reddwarf.utils.sql import (
    SQLDialect, InvalidSQLBuilderInstruction,
    build_insert_query, build_select_query, build_delete_query, build_update_query
)


class MySQLPool:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            print("brand new pool")
            # cls.instance = cls.__new__(cls)
            cls.instance = super(MySQLPool, cls).__new__(cls)
        else:
            print("pool exist")
        return cls.instance

    def __init__(self):
        pass

    async def create_mysql_pool(self, host, port, user, password, db, loop, autocommit=False):
        port = int(port)
        self._pool = await aiomysql.create_pool(
            host=host, port=port, user=user, password=password,
            db=db, loop=loop, autocommit=autocommit
        )
        print("mysql pool created!")

    def get_mysql_pool(self):
        # if self._pool is None:
        #     raise ConnectionError("MySQL Pool has not been created yet!")
        return self._pool


async def select_one(
        dbc, table, *,
        cols=None, where=None, limit=None,
        offset=None, group_by=None
) -> dict:
    sql = build_select_query(
        table=table, cols=cols, where=where,
        limit=limit, offset=offset, group_by=group_by, dialect=SQLDialect.MySQL
    )
    async with dbc.cursor() as cur:
        await cur.execute(sql)
        result_cols = [i[0] for i in cur.description]
        result = dict(zip(result_cols, await cur.fetchone()))
    return result


async def select_many(
        dbc, table, *,
        cols=None, where=None, limit=None,
        offset=None, group_by=None
) -> list[dict]:
    sql = build_select_query(
        table=table, cols=cols, where=where,
        limit=limit, offset=offset, group_by=group_by, dialect=SQLDialect.MySQL
    )
    async with dbc.cursor() as cur:
        await cur.execute(sql)
        result_cols = [i[0] for i in cur.description]
        result = [dict(zip(result_cols, row_tuple)) for row_tuple in await cur.fetchall()]
    return result


async def remove_many(dbc, table, where):
    if not where:
        raise InvalidSQLBuilderInstruction("Empty where in DELETE clause is forbidden")
    async with dbc.cursor() as cur:
        sql = build_delete_query(table, where)
        await cur.execute(sql)
        await cur.execute('commit')


async def insert_many(dbc, table, data: list[dict]):
    if not data:
        return
    async with dbc.cursor() as cur:
        sql, data = build_insert_query(table, data)
        await cur.executemany(sql, data)
        await cur.execute('commit')


async def insert_one(dbc, table, data: dict):
    await insert_many(dbc, table, [data])


async def update_many(dbc, table, where, data):
    if not where:
        raise InvalidSQLBuilderInstruction("Empty where in UPDATE clause is forbidden")
    async with dbc.cursor() as cur:
        sql = build_update_query(table, where, data)
        await cur.execute(sql)
        await cur.execute('COMMIT')
