up:
    docker compose up -d

down:
    docker compose down

psql:
    psql "$DATABASE_URL"

build:
    cargo build

dev-bound:
    cargo run -- target-bounds

dev-single:
    cargo run -- optimize-single-test

dev-update:
    cargo run -- update-db

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

# Documentación con soporte LaTeX (KaTeX)
doc:
    RUSTDOCFLAGS="--html-in-header katex-header.html" cargo doc --no-deps

# Documentación y abrir en el navegador
doc-open:
    RUSTDOCFLAGS="--html-in-header katex-header.html" cargo doc --no-deps --open


