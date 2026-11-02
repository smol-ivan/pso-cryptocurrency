up:
    docker compose up -d

down:
    docker compose down

psql:
    psql "$DATABASE_URL"

run:
    cargo run --release

dev:
    cargo run

migrate-new nombre:
    sqlx migrate add -r {{nombre}}

migrate:
    sqlx migrate run

reset-db:
    sqlx database reset -y

logs:
    docker compose logs -f --tail 100

logs-db:
    docker compose logs -f --tail 100 db

# Exportar metabase
dump-metabase:
    docker compose exec db pg_dump -U app -d metabase > metabase_backup.sql

# Restaurar metabase
restore-metabase:
    docker compose stop metabase
    docker compose exec -T db psql -U app -d postgres -c "DROP DATABASE IF EXISTS metabase;"
    docker compose exec -T db psql -U app -d postgres -c "CREATE DATABASE metabase;"
    docker compose exec -T db psql -U app -d metabase < metabase_backup.sql
    docker compose start metabase

