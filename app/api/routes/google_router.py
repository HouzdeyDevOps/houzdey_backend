# import json
# from fastapi import APIRouter
# from starlette.config import Config
# from starlette.requests import Request
# from starlette.middleware.sessions import SessionMiddleware
# from starlette.responses import HTMLResponse, RedirectResponse
# from authlib.integrations.starlette_client import OAuth, OAuthError

# router = APIRouter()
# router.add_middleware(SessionMiddleware, secret_key="!secret")

# config = Config('.env')
# oauth = OAuth(config)

# CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
# oauth.register(
#     name='google',
#     server_metadata_url=CONF_URL,
#     client_kwargs={
#         'scope': 'openid email profile'
#     }
# )


# @app.get('/')
# async def homepage(request: Request):
#     user = request.session.get('user')
#     if user:
#         data = json.dumps(user)
#         html = (
#             f'<pre>{data}</pre>'
#             '<a href="/logout">logout</a>'
#         )
#         return HTMLResponse(html)
#     return HTMLResponse('<a href="/login">login</a>')


# @app.get('/login')
# async def login(request: Request):
#     redirect_uri = request.url_for('auth')
#     return await oauth.google.authorize_redirect(request, redirect_uri)


# @app.get('/auth')
# async def auth(request: Request):
#     try:
#         token = await oauth.google.authorize_access_token(request)
#     except OAuthError as error:
#         return HTMLResponse(f'<h1>{error.error}</h1>')
#     user = token.get('userinfo')
#     if user:
#         request.session['user'] = dict(user)
#     return RedirectResponse(url='/')


# @app.get('/logout')
# async def logout(request: Request):
#     request.session.pop('user', None)
#     return RedirectResponse(url='/')


# if __name__ == '__main__':
#     import uvicorn
#     uvicorn.run(app, host='127.0.0.1', port=8000)











# # from fastapi import APIRouter, Depends
# # from fastapi.security import OAuth2PasswordBearer
# # import requests
# # from jose import jwt

# # router = APIRouter()
# # oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# # # Replace these with your own values from the Google Developer Console
# # GOOGLE_CLIENT_ID = "1933765501-foivcd7knt25dua10q6r8m3d66nha1g5.apps.googleusercontent.com"
# # GOOGLE_CLIENT_SECRET = "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"
# # GOOGLE_REDIRECT_URI = "your-google-redirect-uri"

# # @router.get("/login/google")
# # async def login_google():
# #     return {
# #         "url": f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
# #     }

# # @router.get("/auth/google")
# # async def auth_google(code: str):
# #     token_url = "https://accounts.google.com/o/oauth2/token"
# #     data = {
# #         "code": code,
# #         "client_id": GOOGLE_CLIENT_ID,
# #         "client_secret": GOOGLE_CLIENT_SECRET,
# #         "redirect_uri": GOOGLE_REDIRECT_URI,
# #         "grant_type": "authorization_code",
# #     }
# #     response = requests.post(token_url, data=data)
# #     access_token = response.json().get("access_token")
# #     user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
# #     return user_info.json()

# # @router.get("/token")
# # async def get_token(token: str = Depends(oauth2_scheme)):
# #     return jwt.decode(token, GOOGLE_CLIENT_SECRET, algorithms=["HS256"])

