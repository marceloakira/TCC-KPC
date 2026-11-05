from datetime import datetime, timedelta
from typing import Optional, Union
from pydantic import BaseModel

from fastapi import HTTPException, Request, Depends
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import HTTPBasic, OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from passlib.context import CryptContext
from starlette.status import HTTP_401_UNAUTHORIZED
from keyphrase_curation import config


SECRET_KEY = config['SECRET_KEY']
SECURITY_ALGORITHM = config['SECURITY_ALGORITHM']
ACCESS_TOKEN_EXPIRE_MINUTES = config['ACCESS_TOKEN_EXPIRE_MINUTES']

basic_security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


def unauthorized(detail: str):
    '''Login missing, invalid or expired: 401, which makes the frontend go
    back to the login page. 403 stays for "logged in, but not allowed".'''
    return HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


class OAuth2PasswordBearerCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: str = '',
        scopes: dict = {},
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            password={"tokenUrl": tokenUrl, "scopes": scopes})  # type: ignore
        super().__init__(flows=flows, scheme_name=scheme_name,
                         auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        header_authorization: str = request.headers.get("Authorization")
        cookie_authorization: str = \
            request.cookies.get("Authorization")  # type: ignore

        header_scheme, header_param = get_authorization_scheme_param(
            header_authorization
        )
        cookie_scheme, cookie_param = get_authorization_scheme_param(
            cookie_authorization
        )
        scheme = ''
        param = ''
        if header_scheme.lower() == "bearer":
            authorization = True
            scheme = header_scheme
            param = header_param

        elif cookie_scheme.lower() == "bearer":
            authorization = True
            scheme = cookie_scheme
            param = cookie_param

        else:
            authorization = False

        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise unauthorized("Not authenticated")
            else:
                return None
        return param


oauth2_scheme = OAuth2PasswordBearerCookie(tokenUrl="/users/token")


def create_access_token(data: dict,
                        expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, SECRET_KEY, algorithm=SECURITY_ALGORITHM)
    return encoded_jwt


def get_user_from_scope(scope: dict):
    authorization = ''
    print('scope: ', scope)
    for header in scope['headers']:
        if header[0] == b'cookie':
            cookie_pairs = header[1].decode('utf-8')
            for cookie_pair in cookie_pairs.split(';'):
                key, value = cookie_pair.strip().split('=')
                if key.lower() == 'authorization':
                    authorization = value.split(' ')[1]
                    authorization = authorization.replace('"', '')
                    break
    if authorization == '':
        return None
    token = authorization.encode('utf-8')
    return jwt.decode(
        token, SECRET_KEY, algorithms=[SECURITY_ALGORITHM])['sub']


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # jwt.decode also rejects tokens whose "exp" has passed
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[SECURITY_ALGORITHM])
    except ExpiredSignatureError:
        raise unauthorized("Token expired")
    except JWTError:
        raise unauthorized("Could not validate credentials")
    username = payload.get("sub")
    if not username or not payload.get("exp"):
        raise unauthorized("Could not validate credentials")
    return username
