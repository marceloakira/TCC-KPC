from datetime import timedelta
from fastapi import \
    APIRouter, Depends, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import RedirectResponse, Response
from fastapi.security import OAuth2PasswordRequestForm, HTTPBasicCredentials
from keyphrase_curation.controller.user_attribution \
    import UserAttributionController
from keyphrase_curation.util.security \
    import OAuth2PasswordBearerCookie, basic_security, \
    create_access_token, get_current_user
from keyphrase_curation import config

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearerCookie(tokenUrl="/users/token")


def cookie_options():
    '''Attributes of the login cookie (legacy interface and API docs).
    An empty COOKIE_DOMAIN makes the cookie valid only for the host that
    set it.'''
    return {
        "domain": config.get('COOKIE_DOMAIN') or None,
        "secure": config['cookie_secure'],
        "samesite": config['cookie_samesite'],
        "httponly": True,
    }


def gen_response_cookie(username: str, redirect: str = "/api/docs"):
    access_token_expires = timedelta(
        minutes=int(config['ACCESS_TOKEN_EXPIRE_MINUTES']))
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )

    token = jsonable_encoder(access_token)
    if redirect is None:
        response = Response(
            headers={"WWW-Authenticate": "Basic"}, status_code=200)
    else:
        response = RedirectResponse(url=redirect)
    response.set_cookie(
        "Authorization",
        value=f"Bearer {token}",
        max_age=14400,
        expires=14400,
        **cookie_options(),
    )
    return response


@router.get("/basic_login")
@router.get("/basic_login/", include_in_schema=False)
async def login_basic(
        credentials: HTTPBasicCredentials = Depends(basic_security)):
    if not credentials:
        response = Response(
            headers={"WWW-Authenticate": "Basic"}, status_code=401)
        return response

    try:
        username = credentials.username
        password = credentials.password
        if not UserAttributionController().\
                validate_password(username, password):
            raise HTTPException(401, detail="Incorrect username or password")
        return gen_response_cookie(username)

    except Exception:
        response = Response(
            headers={"WWW-Authenticate": "Basic"}, status_code=401)
        return response

@router.get("/logout")
@router.get("/logout/", include_in_schema=False)
async def logout(request: Request):
    response = RedirectResponse(url="/users/login")
    response.delete_cookie("Authorization", **cookie_options())
    return response


@router.get("/list")
@router.get("/list/", include_in_schema=False)
async def list_users(user: str = Depends(get_current_user)):
    return UserAttributionController().get_users()


@router.get("/whoami")
@router.get("/whoami/", include_in_schema=False)
async def whoami(user: str = Depends(get_current_user)):
    return {"username": user}


@router.post("/login")
@router.post("/login/", include_in_schema=False)
async def login(request: Request,
                form_data: OAuth2PasswordRequestForm =
                Depends()):
    if not UserAttributionController().validate_password(
            form_data.username, form_data.password):
        raise HTTPException(401, detail="Incorrect username or password")
    
    # Criar token JWT
    access_token_expires = timedelta(
        minutes=int(config['ACCESS_TOKEN_EXPIRE_MINUTES']))
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    
    # Retornar token no response body (para compatibilidade com SPA)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": form_data.username
    }

# Alias para compatibilidade com Swagger UI
@router.post("/token")
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint de token para compatibilidade com OAuth2 padrão"""
    if not UserAttributionController().validate_password(
            form_data.username, form_data.password):
        raise HTTPException(401, detail="Incorrect username or password")
    
    # Criar token JWT
    access_token_expires = timedelta(
        minutes=int(config['ACCESS_TOKEN_EXPIRE_MINUTES']))
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }