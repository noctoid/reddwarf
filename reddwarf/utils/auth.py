import jwt
from datetime import datetime, timedelta


def authenticate_token(token: str, secret: str) -> dict | None:
    """
    token: jwt
    secret: APP SECRET
    return: user dict
    """
    if not token:
        return None
    decoded = jwt.decode(token, secret, algorithms='HS256')
    print(decoded)
    match decoded:
        case {"expire_at": expire_at}:
            if datetime.utcfromtimestamp(expire_at) < datetime.now():
                print(datetime.utcfromtimestamp(expire_at))
                print(datetime.now())
                return None
            return decoded
        case _:
            print("?")
            return None


def create_token(user: dict, secret: str):
    return jwt.encode(
        {**user, "expire_at": (datetime.now()+timedelta(days=24)).timestamp()},
        secret, algorithm='HS256'
    )
