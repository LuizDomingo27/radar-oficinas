-- =============================================================================
-- Migration: criação da tabela `Envios_Radar`
-- =============================================================================
--
-- Contexto: nova área "Envios" do Radar de Oficinas. Armazena, no Neon,
-- os envios de peças às oficinas (peças, minutos, data de envio, matéria-prima
-- etc.), para não depender de re-subir a planilha completa a cada vez — o app
-- sobe apenas os envios NOVOS, como já é feito na tabela `postos`.
--
-- Segurança: usa `CREATE TABLE IF NOT EXISTS` (idempotente, nunca derruba
-- dados existentes) e não contém nenhum DROP/DELETE/TRUNCATE. Seguro para
-- rodar mais de uma vez. NÃO toca em nenhuma outra tabela (ex.: `postos`).
--
-- Nome com maiúsculas/underscore ("Envios_Radar") a pedido do time, para
-- identificar a tabela com facilidade — por isso é sempre referenciada entre
-- aspas no Postgres e com o mesmo case exato no app.
--
-- Como aplicar: `py -3.12 -m app_common.scripts.bootstrap_neon`, que executa
-- este arquivo no endpoint direto do Neon.
-- =============================================================================

create table if not exists public."Envios_Radar" (
    id          bigint generated always as identity primary key,
    -- Impressão digital da linha (SHA-1 do conteúdo + índice de ocorrência).
    -- É a chave anti-duplicação: re-subir a MESMA planilha não insere nada,
    -- e duas linhas idênticas do mesmo arquivo são ambas preservadas.
    row_hash    text not null,
    origem      text,
    ordem       text not null,
    oficina     text not null,
    qtd         integer not null default 0,
    minutos     double precision not null default 0,
    envio       date,                       -- pode ser nulo (326 linhas sem data)
    mp          text,
    pdv         text,
    frete       text,
    situacao    text,
    created_at  timestamptz not null default now()
);

-- Unicidade do row_hash: garante a deduplicação também no nível do banco
-- (defesa em profundidade, além da checagem feita pela aplicação antes do insert).
create unique index if not exists envios_radar_row_hash_uidx
    on public."Envios_Radar" (row_hash);

-- Consulta por número da ordem (tela de consulta por ORDEM).
create index if not exists envios_radar_ordem_idx
    on public."Envios_Radar" (ordem);

-- Filtros/granularidades por data e por oficina.
create index if not exists envios_radar_envio_idx
    on public."Envios_Radar" (envio);
create index if not exists envios_radar_oficina_idx
    on public."Envios_Radar" (oficina);

comment on table public."Envios_Radar" is
    'Envios de peças às oficinas (peças, minutos, data de envio, matéria-prima). Área "Envios" do Radar de Oficinas. Deduplicado por row_hash (insert-only).';
