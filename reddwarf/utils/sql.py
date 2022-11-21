import decimal
from enum import Enum

__all__ = [
    'SQLDialect',
    'DEFAULT_DIALECT',
    'build_select_query',
    'build_update_query',
    'build_insert_query',
    'build_delete_query',
]


class SQLDialect(Enum):
    MySQL = 'mysql'
    ClickHouse = 'clickhouse'


DEFAULT_DIALECT = SQLDialect.MySQL


BASIC_AGGR_FUNCTIONS = (
    'count', 'sum', 'max', 'min', 'avg', 'distinct',
)

CLICKHOUSE_AGGR_FUNCTIONS = (
    'argMax', 'argMin',
)

SUPPORTED_AGGR_FUNCTIONS = {
    SQLDialect.MySQL: BASIC_AGGR_FUNCTIONS,
    SQLDialect.ClickHouse: (*BASIC_AGGR_FUNCTIONS, *CLICKHOUSE_AGGR_FUNCTIONS,),
}

ALLOWED_OPERATORS = (
    '>', '>=', '<', '<=', '!=', 'regexp',
)


class InvalidSQLBuilderInstruction(Exception):
    """Invalid SQL Builder Instruction"""


class UnsupportedSQLDialect(Exception):
    """Unsupported Command Found in selected dialect"""


def build_select_query(
        table,
        cols: list[str | dict] = None,
        where: dict = None,
        limit: int = None,
        offset: int = None,
        group_by: list[str] = None,
        dialect=SQLDialect.MySQL
) -> str:
    return " ".join([
        build_select(cols, dialect=dialect),
        build_from(table),
        build_where(where, dialect=dialect),
        build_window(limit, offset),
        build_group_by(group_by)
    ])


def build_insert_query(table, data, dialect=SQLDialect.MySQL) -> tuple:
    if not data:
        return 0
    cols = data[0].keys()
    if dialect == SQLDialect.ClickHouse:
        return (
            f"INSERT INTO {table} ({','.join(cols)}) VALUES", data
        )
    return (
        # f'INSERT INTO {table}({",".join(cols)}) VALUES ({",".join([":"+col for col in cols])})',
        f'INSERT INTO {table}({",".join(cols)}) VALUES ({",".join([f"%({col})s" for col in cols])})',
        data
    )


def build_update_query(table, where, data, dialect=SQLDialect.MySQL):
    if not data:
        return
    return " ".join([
        f"UPDATE {table} SET",
        ",".join(f"{k}={to_literal(v)}" for k, v in data.items()),
        build_where(where, dialect=dialect)
    ])


def build_delete_query(table, where, dialect=SQLDialect.MySQL):
    return " ".join([
        f"DELETE FROM {table}",
        build_where(where, dialect)
    ])


def build_select(cols: list[str, dict], dialect=DEFAULT_DIALECT) -> str:
    if cols is None:
        return 'SELECT *'
    select_cols = []
    for col in cols:
        match col:
            case str():
                select_cols.append(col)
            case dict():
                select_cols.append(build_func(col))
            case _:
                raise InvalidSQLBuilderInstruction(f"{col}: {type(col)} is invalid for building select")
    return f"SELECT {', '.join(select_cols) if select_cols else '*'}"


def build_from(table: str):
    return f"FROM {table}"


def build_group_by(cols: list):
    if cols is None:
        return ''
    return f"GROUP BY {', '.join(cols)}"


def build_window(limit: int = None, offset: int = None):
    match limit, offset:
        case int(), int():
            return f"LIMIT {limit} OFFSET {offset}"
        case int(), None:
            return f"LIMIT {limit}"
        case None, int():
            return f"OFFSET {offset}"
        case None, None:
            return ''
        case _:
            raise InvalidSQLBuilderInstruction("invalid limit and offset")


def build_func(func_col: dict, dialect=DEFAULT_DIALECT):
    as_name = func_col.pop('as') if 'as' in func_col else None
    func_col = {k.lower(): v for k, v in func_col.items()}
    match func_col:
        case {"aggr": func, "col": col_name}:
            if func not in SUPPORTED_AGGR_FUNCTIONS[dialect]:
                raise InvalidSQLBuilderInstruction(f"{func} is not supported")
            return f"{func}({col_name}) {col_name if as_name is None else as_name}"
        case _:
            raise InvalidSQLBuilderInstruction(f"An unsupported function is provided")


def to_literal(v):
    match v:
        case str():
            return f"'{v}'"
        case _:
            return str(v)


def build_where(condition, dialect):
    if condition is None:
        return ''

    def translate_dialect(column_, op_, val_):
        match op_:
            case "regexp":
                if dialect == SQLDialect.ClickHouse:
                    return f"match({column_}, {to_literal(val_)})"
                else:
                    return f"{column_} REGEXP {to_literal(val_)}"
            case _:
                return f"{column_} {op_} {to_literal(val_)}"
    where_statement = []
    for column, col_cond in condition.items():
        match col_cond:
            case list() | tuple():
                where_statement.append(f"{column} IN ({','.join(map(to_literal, col_cond))})")
            case dict():
                # {">": 2, "<": 3}
                composed_condition = []
                for op, val in col_cond.items():
                    where_statement.append(translate_dialect(column, op, val))
            case _:
                where_statement.append(f"{column} = {to_literal(col_cond)}")
    return 'WHERE '+' AND '.join(where_statement)
