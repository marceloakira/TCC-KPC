from reactpy import component, html, use_state, event
from reactpy.html import \
    input, label, button, form, br
from aiohttp import ClientSession


@component
def LoginAPI():
    username, set_username = use_state("")
    password, set_password = use_state("")
    http_status, set_http_status = use_state(0)
    cookie, set_cookie = use_state("")

    @event(prevent_default=True)
    async def submit_login(event):
        form_data: dict = {
            "username": username,
            "password": password
        }
        async with ClientSession(base_url="http://localhost:3132") as session:
            async with session.post(
                url="/users/login",
                data=form_data,
                headers={"content-type": "application/x-www-form-urlencoded"}
            ) as resp:
                set_http_status(resp.status)
                if 'Set-Cookie' in resp.headers:
                    set_cookie(resp.headers['Set-Cookie'])

    def login_form(error=False, cookie_ok=False):
        header = html.header("")
        title = html.h1("Login")
        if error:
            title = html.h1("Incorrect username or password")
        elif cookie_ok:
            cookie1 = cookie.replace('"', '\\"')
            cookie2 = cookie1.replace('HttpOnly; ', '')
            title = html.h1("Redirecting...")
            header = html.header(
                html.script(
                    f'document.cookie="{cookie2}";'
                    f'window.location.href = "/keyphrase_curation/{username}";'
                )
            )
        return html._(
            header,
            title,
            form(
                label("Username: "),
                input({
                    "type": "text",
                    "name": "username",
                    "onBlur": lambda event: set_username(
                        event['target']['value'])
                }),
                br(),
                label("Password: "),
                input({
                    "type": "password",
                    "name": "password",
                    "onBlur": lambda event: set_password(
                        event['target']['value']),
                }),
                br(),
                button({
                    "onClick": submit_login,
                    "name": "login",
                    "value": "Login",
                }, "Login")
            )
        )

    if http_status == 401:
        return html.div(
            login_form(error=True)
        )
    elif http_status == 200:
        return html.div(
            login_form(cookie_ok=True)
        )
    else:
        return html.div(
            login_form()
        )
