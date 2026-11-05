#!/bin/sh
# Backup periódico dos dados do KPC: anotações e cadastro de usuários.
# Roda no serviço "backup" do docker-compose; /data é a pasta de dados
# (somente leitura) e /backups, onde os arquivos .tar.gz ficam.
#   sh /backup.sh        a cada BACKUP_INTERVAL_HOURS horas, para sempre
#   sh /backup.sh once   um backup só (ex.: antes de uma atualização)
set -u

interval_hours="${BACKUP_INTERVAL_HOURS:-6}"
retention_days="${BACKUP_RETENTION_DAYS:-30}"

backup() {
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    paths=""
    for path in annotations attributions.toml; do
        [ -e "/data/$path" ] && paths="$paths $path"
    done
    if [ -z "$paths" ]; then
        echo "nada para copiar em /data"
        return 1
    fi
    # escreve num arquivo temporário: um backup interrompido não fica com
    # cara de backup completo
    tmp="/backups/.kpc-$stamp.tar.gz.tmp"
    # shellcheck disable=SC2086
    if tar -czf "$tmp" -C /data $paths; then
        mv "$tmp" "/backups/kpc-$stamp.tar.gz"
        echo "backup criado: kpc-$stamp.tar.gz"
    else
        rm -f "$tmp"
        echo "falha no backup $stamp"
        return 1
    fi
    find /backups -name 'kpc-*.tar.gz' -mtime +"$retention_days" -delete
}

if [ "${1:-}" = "once" ]; then
    backup
    exit $?
fi

while true; do
    backup
    sleep $((interval_hours * 3600))
done
