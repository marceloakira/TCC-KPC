# Imagem de produção do backend (deploy/docker-compose.yml).
# O código vai dentro da imagem; os dados (dataset/) vêm de um volume.
# Para desenvolvimento com Docker, use launcher/Dockerfile.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential: algumas dependências (pycld2, multi-rake) compilam código C
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
# PyTorch só para CPU: a versão padrão traz as bibliotecas CUDA (vários GB)
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu torch==2.2.2 \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts

# Usuário sem privilégios, com o mesmo UID do dono da pasta de dados no
# servidor (KPC_UID em deploy/.env), para poder gravar as anotações
ARG KPC_UID=1000
RUN useradd --create-home --uid "$KPC_UID" kpc
USER kpc

EXPOSE 3132

# Um único processo: os arquivos de anotação não têm trava entre processos
CMD ["uvicorn", "keyphrase_curation.api.main:app", \
     "--host", "0.0.0.0", "--port", "3132", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
