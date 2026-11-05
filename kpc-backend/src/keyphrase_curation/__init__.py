
from dotenv import dotenv_values, find_dotenv
from pathlib import Path
import os
import sys

config = None
root_path = Path(__file__).resolve().parents[2]
env_filepath = find_dotenv(usecwd=True) or str(root_path / ".env")
sys.path.append(str(root_path))

_REQUIRED_KEYS = [
    "DATASET_RELATIVE_PATH",
    "ATTRIBUTIONS_FILENAME",
    "CLUSTER_IDS_LENGTH",
    "CURATED_KEYPHRASES_LENGTH",
    "SECRET_KEY",
]

# Keys that environment variables can set, overriding the .env file
# (the Docker deployment has no .env file)
_ENV_KEYS = _REQUIRED_KEYS + [
    "OPENAI_API_TOKEN",
    "OPENAI_API_TEMPERATURE",
    "OPENAI_API_MODEL",
    "OPENAI_API_MAX_TOKENS",
    "SECURITY_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "COOKIE_DOMAIN",
    "COOKIE_PATH",
    "COOKIE_SECURE",
    "COOKIE_SAMESITE",
    "CORS_ORIGINS",
    "LEGACY_UI_ENABLED",
    "API_DOCS_ENABLED",
]


def as_bool(value, default=False):
    '''"1", "true", "yes" and "on" are true; None or "" is the default'''
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def init_config():
    config = dotenv_values(env_filepath) or {}
    config.update({
        key: os.environ[key] for key in _ENV_KEYS if key in os.environ})
    missing_keys = [key for key in _REQUIRED_KEYS if not config.get(key)]

    if missing_keys:
        missing = ", ".join(missing_keys)
        raise RuntimeError(
            f"Configuracao incompleta em {env_filepath}: {missing}"
        )

    config['root_path'] = str(root_path)
    dataset_path = f"{root_path}/{config['DATASET_RELATIVE_PATH']}"
    config['dataset_path'] = dataset_path
    config['tests_path'] = f"{root_path}/tests"
    config['fixtures_path'] = f"{config['tests_path']}/fixtures"
    attributions_filepath = f"{dataset_path}/{config['ATTRIBUTIONS_FILENAME']}"
    config['attributions_filepath'] = attributions_filepath
    config['cluster_ids_length'] = int(config['CLUSTER_IDS_LENGTH'])
    config['curated_keyphrases_length'] = \
        int(config['CURATED_KEYPHRASES_LENGTH'])
    config['embeddings_path'] = f"{dataset_path}/keyphrases/embeddings"
    config['collected_keyphrases_path'] = \
        f"{dataset_path}/keyphrases/collected"

    # Production settings (defaults keep the local development setup)
    cors_origins = config.get('CORS_ORIGINS')
    if cors_origins is None:
        # frontend dev server (npm run dev:mvvm) and preview
        cors_origins = 'http://localhost:5174,http://localhost:4174'
    config['cors_origins'] = [
        origin.strip() for origin in cors_origins.split(',')
        if origin.strip()]
    config['cookie_secure'] = as_bool(config.get('COOKIE_SECURE'), False)
    config['cookie_samesite'] = config.get('COOKIE_SAMESITE') or 'lax'
    config['legacy_ui_enabled'] = \
        as_bool(config.get('LEGACY_UI_ENABLED'), True)
    config['api_docs_enabled'] = as_bool(config.get('API_DOCS_ENABLED'), True)
    return config


config = init_config()

VERSION = "0.1.0"
