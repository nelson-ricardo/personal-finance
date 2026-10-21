#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE budget_app_dev' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'budget_app_dev')\gexec
    SELECT 'CREATE DATABASE budget_app_prod' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'budget_app_prod')\gexec
EOSQL
