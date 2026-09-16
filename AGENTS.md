<!-- BEGIN:Python-agent-rules -->

# This is NOT the python you know

This block is written and re-added by Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:python-agent-rules -->

# Como trabalhamos neste repositório

As regras abaixo não são preferências de estilo: são o que separa uma mudança
aceita de uma rejeitada. Quando algo aqui conflitar com o "jeito mais rápido",
vale o que está escrito aqui.

## Arquitetura em camadas

O repositório tem **dois formatos de área**, e nenhum dos dois é opcional:

- **Dashboards Streamlit** (`app_postos/`, `app_envios/`, `app_recebimento/`):
  `core/` → `services/` → `ui/` → `dashboard.py`.
- **Pipeline do Radar** (`app_oficinas/`): `config.py` → `infra/` → `domain/` →
  `services/`, que gera os JSON em `data/` consumidos pela SPA em `web/`. Não
  tem camada `ui/` — a interface dele é a SPA.

Acima dos dois está `app_common/`, o **código que é de todos**. Nada nele pode
importar uma área; são as áreas que importam dele:

| Módulo | O que é |
|---|---|
| `theme.py` | a paleta, declarada uma única vez para o app inteiro |
| `formatting.py` | formatação pt-BR, divisão segura, `row_hash`, "selecionar todos" |
| `errors.py` | a fábrica de `error_boundary`/`guard` por área |
| `neon_client.py` | o ÚNICO acesso ao banco |
| `movimentacao/` | o núcleo de Envios e Recebimento (ver abaixo) |

`app_common/movimentacao/` existe porque **Envios e Recebimento são a mesma
tela** sobre contratos de dados diferentes. Ele tem as suas próprias camadas
(`area.py` → `analytics.py`/`data_loader.py` → `ui/`), e cada área declara só o
que a distingue — tabela, colunas e vocabulário — num `AreaMovimentacao` dentro
do seu `core/config.py`. **Área nova de movimentação não copia a irmã: declara o
seu descritor.**

Nos dashboards, a dependência corre em **uma direção só**: `ui → services → core`.

| Camada | Responsabilidade | Não pode |
|---|---|---|
| `core/` | config, contrato de colunas, tratamento de erro, utilitários | conhecer banco ou planilha |
| `services/` | regra de negócio, leitura/gravação, agregações | importar `streamlit` |
| `ui/` | apresentação: HTML, CSS, gráficos, componentes | conter regra de negócio ou cálculo |
| `dashboard.py` | orquestra: navbar → carga → página ativa | fazer cálculo próprio |

- **Agregação é de `services/`.** `groupby`, `agg`, média, soma de indicador e
  divisão de taxa não entram em função que desenha. A única conta tolerada na
  `ui/` é sobre a própria decisão de tela — por exemplo, contar quantas linhas o
  filtro deixou de fora para avisar o usuário.
- A UI recebe valores **já formatados** ou DataFrames prontos.
- **Exceção conhecida:** `app_common/errors.py` importa `streamlit` de propósito
  — é ele quem converte exceção em mensagem de tela. E `app_common/neon_client.py`
  também, porque lê a conexão de `st.secrets`, o que faz qualquer `services/`
  que grave ou leia depender de `streamlit` indiretamente. São os dois únicos
  pontos onde a dependência atravessa camada; qualquer terceiro é erro.
- O shell (`streamlit_app.py`) importa cada módulo de forma **tardia e
  protegida**: uma área quebrada nunca pode derrubar as outras.

- **Serviço não se importa através da `ui`.** Se `dashboard.py` precisa de uma
  função de `services/`, ele importa de `services/` — nunca reexportada por um
  componente de tela.

## Desenvolvimento limpo

- **Nada órfão.** Toda função, constante, arquivo e coluna precisa ter quem a
  use em código de produção. Coisa usada só por teste é código morto — apague.
  Antes de fechar, faça a busca e confirme.
- **Uma fonte de verdade.** Nome de tabela, cabeçalho de planilha, paleta e
  rótulo se declaram **uma vez** (em `core/config.py` ou num módulo
  compartilhado) e são importados. Copiar e colar constante entre áreas é erro.
- **Nomes dizem o que a coisa é** em português do negócio; `snake_case` no
  código. Cabeçalho cru de planilha só aparece em `RawColumns`; do resto do
  código para dentro, só o nome padronizado.
- **Docstring explica o porquê**, não o que a linha faz. Se a decisão foi
  tomada por um motivo não óbvio (dedup por hash, ordem fixa de campos,
  `st.html` em vez de `st.markdown`), esse motivo fica escrito ali.
- **Mudança mínima.** Não reformate, renomeie nem "melhore" o que está fora do
  escopo do pedido. Se achar um problema vizinho, relate — não conserte junto.
- **Imitar o vizinho.** Área nova espelha a estrutura da área mais parecida que
  já existe. Divergir só com motivo declarado.

## Erros e exceções

- **O app nunca mostra traceback.** Todo ponto de entrada de tela passa por
  `error_boundary` / `guard`: mensagem amigável na tela, detalhe técnico
  recolhido, log no servidor.
- A mensagem diz **o que o usuário faz agora** ("importe a planilha em
  Lançamento de Dados"), não só o que falhou.
- `except Exception` só é aceitável quando o objetivo é **converter** a falha em
  mensagem ou em erro de domínio — nunca para engolir em silêncio.
- Estado vazio, filtro sem resultado e credencial ausente são **casos previstos**
  com tela própria, não erro.

## Testes

- Toda função de `core/` e `services/` tem teste. Rode a suíte inteira antes de
  dar qualquer coisa por pronta: `py -3.12 -m pytest tests/`.
- **Teste não toca no banco real** — use os fakes em `tests/`. Teste que precisa
  de rede não entra.
- Teste o caminho torto também: coluna faltando, valor nulo, data inválida,
  DataFrame vazio, duplicata.
- **Rode o linter junto com a suíte**, porque testes não pegam nome quebrado
  dentro de função nem import órfão:
  `py -3.12 -m ruff check --select F821,F811,F401 app_*`
- Antes de apagar ou renomear qualquer nome, **procure quem o usa** — inclusive
  quem importa *através* do módulo (reexport). Um `grep` só dentro do arquivo
  não basta.
- `tests/common/test_imports.py` importa todo módulo do app. Se você criar um
  pacote novo, acrescente-o ali.
- Suíte vermelha bloqueia commit. Sempre.

## Banco de dados (Neon)

- **Importação é insert-only.** Nada de `DELETE`, `DROP`, `TRUNCATE` ou
  sobrescrita em código de aplicação. Quem já está no banco, fica.
- **Deduplicação por `row_hash`**: re-subir a mesma planilha insere zero linhas.
- **Migração é idempotente**: `CREATE TABLE / INDEX IF NOT EXISTS`, um arquivo
  por mudança em `db_migrations/migrations/`, com data no nome.
- **DDL simples nas migrações.** O divisor de SQL corta em todo `;` e ignora
  aspas — nada de `;` dentro de literal, nem de blocos `$$ ... $$`.
- Antes de qualquer carga em lote ou mudança que **altere dados**, tire a cópia:
  `py -3.12 -m app_common.scripts.backup_neon`.

## Ambiente e dependências

- O interpretador do projeto é o **Python 3.12** (`py -3.12`), casando com
  `runtime.txt`. Outro Python não tem as libs do app.
- Antes de subir o app, teste **no ambiente local**, de verdade: abra a tela,
  clique, confira o número.
- `requirements.txt` é **pin exato**, inclusive transitivas. Dependência nova só
  entra com versão travada e com a suíte verde depois.
- Sempre avalie a performance do recurso que você criou (consulta, agregação,
  render) antes de considerá-lo pronto.

## Documentação obrigatória do fluxo do produto

Toda implementação que altere ou crie comportamento visível do aplicativo deve
atualizar, na mesma mudança, `docs/guia-fluxo-operacional.html`.

- Explique o propósito em linguagem de negócio e descreva o fluxo completo, do
  início ao resultado.
- Registre os papéis envolvidos, a tela usada, os dados de entrada, as decisões,
  as exceções e o que o sistema salva.
- Atualize a simulação end-to-end quando a implementação afetar autenticação,
  Ordem Mestre, conferências, distribuição, entrega ao PUP, conclusão ou
  acompanhamento.
- Confirme que nomes de telas, botões, status, permissões e resultados no guia
  continuam iguais ao comportamento do app.

## Definição de pronto

Uma mudança de produto só está completa quando **todos** estes itens estão
verdadeiros:

1. Camadas respeitadas, sem regra de negócio na UI.
2. Nenhum código órfão ou obsoleto deixado para trás.
3. Erros tratados; nenhuma tela capaz de mostrar traceback.
4. Testes escritos e a suíte inteira passando no `py -3.12`.
5. App aberto e conferido localmente.
6. `docs/guia-fluxo-operacional.html` atualizado na mesma mudança.
7. Commit **só com permissão** — e, quando autorizado, um commit único e
   coerente, com a mensagem explicando o porquê.
