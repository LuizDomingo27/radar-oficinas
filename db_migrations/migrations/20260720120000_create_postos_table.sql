-- =============================================================================
-- Migration: criação da tabela `postos`
-- =============================================================================
--
-- Contexto: migração do APP_Postos de SQLite (`Dataset/postos.db`) para
-- Supabase. Esta é a única tabela nova exigida pelo app — o restante do
-- schema já existe e NÃO é tocado por este script.
--
-- Segurança: usa `CREATE TABLE IF NOT EXISTS` (idempotente, nunca derruba
-- dados existentes) e não contém nenhum DROP/DELETE/TRUNCATE. Seguro para
-- rodar mais de uma vez.
--
-- Como aplicar: cole e execute este arquivo no Supabase Dashboard →
-- SQL Editor (ou via `supabase db push`, se estiver usando a CLI).
-- =============================================================================

create table if not exists public.postos (
    id                bigint generated always as identity primary key,
    frete             text not null,
    mp                text not null,
    oficina           text not null,
    data_efetivos     date not null,
    qtd_efetivos      integer not null default 0,
    data_trabalhados  date not null,
    qtd_trabalhados   integer not null default 0,
    contratacoes      integer not null default 0,
    demissoes         integer not null default 0,
    semana            integer not null,
    created_at        timestamptz not null default now()
);

-- Índices para acelerar a checagem de duplicidade (Oficina + MP + Semana)
-- feita pela aplicação antes de cada inserção manual, e os filtros mais
-- comuns do dashboard.
create index if not exists postos_oficina_mp_semana_idx
    on public.postos (oficina, mp, semana);

create index if not exists postos_semana_idx
    on public.postos (semana);

-- RLS habilitado por padrão (boa prática recomendada pelo Supabase). O app
-- acessa esta tabela com a service_role key, que ignora RLS — nenhuma
-- policy é necessária aqui. Se no futuro a tabela precisar ser lida com a
-- anon key, adicione policies explícitas de select/insert.
alter table public.postos enable row level security;

comment on table public.postos is
    'Lançamentos semanais de efetivos/trabalhados/contratações/demissões por oficina e matéria-prima. Migrado do SQLite (Dataset/postos.db) do APP_Postos.';
