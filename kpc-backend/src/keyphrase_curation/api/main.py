import os

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic
from fastapi import Security
from keyphrase_curation import as_bool, config
from keyphrase_curation.api import annotation_file, user, keyphrase, topic, cluster
from keyphrase_curation.util.security \
    import get_current_user

api_docs_enabled = config['api_docs_enabled']

app = FastAPI(
    docs_url='/api/docs' if api_docs_enabled else None,
    redoc_url=None,
    openapi_url='/openapi.json' if api_docs_enabled else None)

# CORS_ORIGINS: origins allowed to call the API from another address
# (the dev server); empty in production, where the frontend and the API
# share the same address
origins = config['cors_origins']
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # credentials are never allowed together with any origin ("*")
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"]
    )

app.include_router(topic.router, prefix="/topic", tags=["topics"])
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(keyphrase.router, prefix="/keyphrases", tags=["keyphrases"])
app.include_router(cluster.router, prefix="/clusters", tags=["clusters"])
app.include_router(
    annotation_file.router,
    prefix="/annotation_files",
    tags=["annotation files"])

# Legacy ReactPy interface, served at the root of the backend
if config['legacy_ui_enabled']:
    from keyphrase_curation.components.app import bind_root
    bind_root(app)


if api_docs_enabled:
    @app.get("/openapi.json")
    async def get_open_api_endpoint(
            user: str = Depends(get_current_user)):
        return JSONResponse(
            get_openapi(title="FastAPI", version='1', routes=app.routes))

    @app.get("/api/docs")
    @app.get("/api/docs/", include_in_schema=False)
    async def get_documentation(
            credentials: str = Security(HTTPBasic())):
        return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

if __name__ == "__main__":
    uvicorn.run(
        "keyphrase_curation.api.main:app",
        host=os.getenv("KPC_HOST", "127.0.0.1"),
        port=int(os.getenv("KPC_PORT", "3132")),
        reload=as_bool(os.getenv("KPC_RELOAD"), True))
