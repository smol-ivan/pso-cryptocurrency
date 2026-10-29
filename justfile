up:
    docker compose up -d

down:
    docker compose down

psql:
    psql "$DATABASE_URL"

run:
    cargo run --release

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
