# KPC em produção

Esta pasta sobe o KPC num servidor Linux com Docker. São três serviços:

| Serviço   | O que faz |
|-----------|-----------|
| `web`     | Caddy: serve o frontend compilado, repassa `/api/*` ao backend e obtém o certificado HTTPS sozinho |
| `backend` | API FastAPI; não tem porta aberta, só o `web` fala com ele |
| `backup`  | a cada 6 horas, compacta `annotations/` e `attributions.toml` em `backups/` e guarda 30 dias |

```
navegador ──► web (portas 80/443) ──► /api/*  ──► backend:3132 ──► data/
                                  └─► demais  ──► frontend (index.html)
```

Os dados ficam em `deploy/data/`, fora das imagens: atualizar ou recriar os
contêineres não apaga anotações.

## Requisitos

- Servidor Linux com Docker Engine e o plugin Compose (`docker compose version`;
  no Debian, veja "Instalar o Docker no Debian" abaixo).
- 2 GB de RAM no mínimo (4 GB recomendado) e uns 10 GB livres de disco
  (o backend usa PyTorch).
- Para HTTPS: um domínio apontando para o servidor e as portas 80 e 443 liberadas.
  Sem domínio, dá para usar só HTTP (`SITE_ADDRESS=:80`) para testes.
  Se o servidor já usa o Nginx nessas portas, veja "Servidor que já usa o Nginx".

## Primeira instalação

1. Baixe o código e crie a configuração:

   ```bash
   git clone <endereço do repositório> TCC-KPC
   cd TCC-KPC/deploy
   cp .env.example .env
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   id -u
   ```

   Edite o `.env`: cole a chave gerada em `SECRET_KEY`, o resultado de
   `id -u` em `KPC_UID` e preencha `SITE_ADDRESS` com o domínio
   (ou deixe `:80`).

2. Prepare a pasta de dados com as keyphrases e os embeddings:

   ```bash
   mkdir -p data backups
   cp -r ../kpc-backend/dataset/keyphrases data/
   ```

   O cadastro e as anotações começam vazios. Para levar as anotações já
   existentes no repositório, copie também `../kpc-backend/dataset/annotations`
   para `data/`. Não copie o `attributions.toml` de uma máquina de
   desenvolvimento: ele tem contas de teste.

3. Suba os serviços. A primeira vez demora, porque o PyTorch é baixado:

   ```bash
   docker compose up -d --build
   docker compose ps
   docker compose logs -f backend
   ```

4. Cadastre os usuários (veja abaixo) e acesse `https://<domínio>`
   (ou `http://<ip-do-servidor>` com `SITE_ADDRESS=:80`).

## Servidor que já usa o Nginx

Quando o Nginx do servidor já atende as portas 80/443 (caso dos servidores
argmap da UFG), ele continua cuidando do HTTPS e repassa o endereço do KPC
para o Caddy, que passa a escutar só dentro da máquina:

```
navegador ─► Nginx (80/443, HTTPS) ─► Caddy (127.0.0.1:8081) ─► frontend e /api
```

1. No `deploy/.env`, antes do `docker compose up`:

   ```
   SITE_ADDRESS=:80
   HTTP_PORT=127.0.0.1:8081
   HTTPS_PORT=127.0.0.1:8443
   ```

2. Crie o site no Nginx a partir de `nginx-kpc.conf.example` (os comandos
   estão no próprio arquivo) e gere o certificado com o `certbot --nginx`.

## Instalar o Docker no Debian

Repositório oficial do Docker (os pacotes do Debian são antigos demais
para este `docker-compose.yml`). No Debian 11 sem `curl`, com `wget`:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates wget
sudo install -m 0755 -d /etc/apt/keyrings
sudo wget -qO /etc/apt/keyrings/docker.asc https://download.docker.com/linux/debian/gpg
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release; echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Saia e entre de novo no SSH para o grupo `docker` valer. Quem está nesse
grupo controla o Docker, o que equivale a ter acesso de administrador.

## Usuários e atribuições

O script `manage_users.py` grava o `attributions.toml` e cria os arquivos de
anotação em branco. As mudanças valem na hora, sem reiniciar nada.

```bash
# anotadores (pede a senha duas vezes)
docker compose exec backend python scripts/manage_users.py add maria --topics death_penalty marijuana_legalization
# senha aleatória, mostrada uma única vez
docker compose exec backend python scripts/manage_users.py add joao --generate --topics death_penalty
# mais tópicos para quem já existe
docker compose exec backend python scripts/manage_users.py assign joao gun_control
# adjudicador: depois que os dois anotadores do tópico existem
docker compose exec backend python scripts/manage_users.py add ana --generate
docker compose exec backend python scripts/manage_users.py adjudicator ana death_penalty --annotators maria joao
# trocar senha e conferir o cadastro
docker compose exec backend python scripts/manage_users.py password maria
docker compose exec backend python scripts/manage_users.py list
```

Tópicos com embeddings (os únicos que abrem a tela de agrupamento):
`cloning`, `death_penalty`, `gun_control`, `marijuana_legalization`,
`minimum_wage` e `school_uniforms`. O script recusa `abortion` e
`nuclear_energy`, que ainda não têm embeddings.

## Operação

Atualizar para uma nova versão do código:

```bash
git pull
docker compose run --rm backup once
docker compose up -d --build
```

Backup manual: `docker compose run --rm backup once`.

Restaurar um backup (o estado atual é copiado antes, por segurança):

```bash
docker compose stop backend
docker compose run --rm backup once
tar -xzf backups/kpc-AAAAMMDDTHHMMSSZ.tar.gz -C data
docker compose start backend
```

Os backups ficam no mesmo disco do servidor. Copie a pasta `backups/` para
outra máquina ou para o armazenamento da instituição com regularidade
(por exemplo, `rsync` agendado).

Parar tudo: `docker compose down` (dados e backups continuam nas pastas).
Trocar a `SECRET_KEY` desconecta todos os usuários.

## Testar o build de produção no Windows, sem Docker

Com o backend rodando como de costume, num PowerShell em `kpc-frontend`:

```powershell
$env:VITE_API_BASE_URL = "/api"; npm run build:mvvm
npm run preview:mvvm
```

Abra `http://localhost:4174`. O `preview` repassa `/api` ao backend em
`localhost:3132`, como o Caddy faz no servidor. Feche esse terminal depois
(ou rode `Remove-Item Env:VITE_API_BASE_URL`), senão o próximo build também
usará `/api`.

## Limitações conhecidas

- O backend roda num processo só, porque os arquivos JSON não têm trava.
  Atende poucas pessoas ao mesmo tempo; cada ação leva de 0,5 a 2 segundos.
- Não há limite de tentativas de login: prefira senhas geradas (`--generate`).
- O login fica salvo no navegador pelo tempo de `ACCESS_TOKEN_EXPIRE_MINUTES`.
- A interface antiga (ReactPy) e a documentação `/api/docs` não ficam
  disponíveis em produção.
