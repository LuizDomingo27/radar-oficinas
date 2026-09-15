-- =============================================================================
-- Migration: criação da tabela `Recebimento_Radar`
-- =============================================================================
--
-- Contexto: nova área "Recebimento" do Radar de Oficinas. Armazena, no Neon,
-- os recebimentos de peças das oficinas (peças cortadas, minutos, data de
-- recebimento, matéria-prima), para não depender de re-subir a planilha
-- completa a cada vez — o app sobe apenas os recebimentos NOVOS, como já é
-- feito nas tabelas `postos` e `Envios_Radar`.
--
-- Segurança: usa `CREATE TABLE IF NOT EXISTS` (idempotente, nunca derruba
-- dados existentes) e não contém nenhum DROP/DELETE/TRUNCATE. Seguro para
-- rodar mais de uma vez. NÃO toca em nenhuma outra tabela.
--
-- Nome com maiúsculas/underscore ("Recebimento_Radar") a pedido do time, para
-- identificar a tabela com facilidade — por isso é sempre referenciada entre
-- aspas no Postgres e com o mesmo case exato no app.
-- =============================================================================

create table if not exists public."Recebimento_Radar" (
    id           bigint generated always as identity primary key,
    -- Impressão digital da linha (SHA-1 do conteúdo + índice de ocorrência).
    -- É a chave anti-duplicação: re-subir a MESMA planilha não insere nada,
    -- e duas linhas idênticas do mesmo arquivo são ambas preservadas.
    row_hash     text not null,
    ordem        text not null,
    oficina      text not null,
    qtd          integer not null default 0,
    minutos      double precision not null default 0,
    recebimento  date,                       -- data do recebimento (coluna DIA)
    mp           text,
    created_at   timestamptz not null default now()
);

-- Unicidade do row_hash: garante a deduplicação também no nível do banco
-- (defesa em profundidade, além da checagem feita pela aplicação antes do insert).
create unique index if not exists recebimento_radar_row_hash_uidx
    on public."Recebimento_Radar" (row_hash);

-- Consulta por número da ordem (tela de consulta por ORDEM).
create index if not exists recebimento_radar_ordem_idx
    on public."Recebimento_Radar" (ordem);

-- Filtros/granularidades por data e por oficina.
create index if not exists recebimento_radar_recebimento_idx
    on public."Recebimento_Radar" (recebimento);
create index if not exists recebimento_radar_oficina_idx
    on public."Recebimento_Radar" (oficina);

-- RLS habilitado por padrão (boa prática). O app acessa via string de conexão
-- direta do Neon; nenhuma policy é necessária aqui.
alter table public."Recebimento_Radar" enable row level security;

comment on table public."Recebimento_Radar" is
    'Recebimentos de peças das oficinas (peças cortadas, minutos, data, matéria-prima). Área "Recebimento" do Radar de Oficinas. Deduplicado por row_hash (insert-only).';
