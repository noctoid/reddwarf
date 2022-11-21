import aiomysql


async def create_mysql_pool(host, port, user, password, db, loop, autocommit=False):
    return await aiomysql.create_pool(
        host=host, port=port, user=user, password=password,
        db=db, loop=loop, autocommit=autocommit
    )
