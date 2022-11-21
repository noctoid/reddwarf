import jwt
from datetime import datetime, timedelta

from reddwarf.services.config_service import BaseConfig


def make_salt():
    return 'salty-as-f'


def authenticate_token(token: str) -> dict | None:
    """
    token: jwt
    secret: APP SECRET
    return: user dict
    """
    SECRET = BaseConfig().get_config()['DEFAULT']['secret']
    if not token:
        return None
    decoded = jwt.decode(token, SECRET, algorithms='HS256')
    match decoded:
        case {"expire_at": expire_at}:
            if datetime.utcfromtimestamp(float(expire_at)) < datetime.now():
                return None
            return decoded
        case _:
            return None


def create_token(user: dict):
    SECRET = BaseConfig().get_config()['DEFAULT']['secret']
    return jwt.encode(
        {**user, "expire_at": str((datetime.now()+timedelta(days=24)).timestamp())},
        SECRET, algorithm='HS256'
    )
