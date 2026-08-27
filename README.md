# Radar de Oficinas

Aplicação para medir a eficiência das oficinas (parceiros) e correlacionar com
os treinamentos, consolidando as planilhas de **produção, absenteísmo,
eficiência e treinamentos** numa base única.

## Estado atual — Fase 5: Dashboard (três telas)

Pipeline concluído da Fase 1 à Fase 5:

1. **De-Para** — dimensão canônica de oficinas: cada variação de nome, espalhada
   pelas planilhas, é reunida sob um `oficina_id` único. É a base que faz as
   fontes conversarem.
2. **ETL & consolidação** — as sete planilhas viram tabelas-fato
   (`fato_producao`, `fato_absenteismo`, `fato_eficiencia`, `fato_treino`) já
   ligadas ao `oficina_id` e com o período normalizado.
3. **Métricas** — produtividade (Σpeças ÷ Σminutos) e absenteísmo
   (1 − Σtrab ÷ Σefetivos), em mês/semana; e a **eficiência oficial** lida
   direto das planilhas de estoque (a coluna que a própria planilha calcula:
   média das últimas 4 semanas de entrega ÷ capacidade 100%) — um valor atual
   por oficina, o mesmo número que a equipe acompanha.
4. **Motor de impacto** — para cada oficina treinada, compara a métrica **antes**
   e **depois** do treino (janela anual, o ano do treino é buffer) e contrasta
   com um **grupo de controle** de não treinadas (diferença-em-diferenças).
   Onde falta a janela pré ou pós, a linha recebe status `sem_pre`/`sem_pos`/
   `sem_dado` — nunca some. Saída: `impacto_por_oficina.json`, `impacto_coorte.json`.
5. **Dashboard** — três telas sobre um payload único (`dashboard.json`,
   consolidado a partir das saídas anteriores, sem reabrir planilhas):
   **Ranking geral** (as três métricas por oficina, com semáforo), **Ficha da
   oficina** (linha do tempo de cada métrica com os treinamentos marcados) e
   **Impacto do treinamento** (dif-em-dif por coorte + oficinas com antes ×
   depois medido). Frontend HTML/CSS/JS separado, ECharts via CDN, ícones SVG.

## Arquitetura (camadas com responsabilidade única)

```
app_oficinas/
  domain/     # modelos puros (Oficina, VarianteNome, RegistroNome) — sem I/O
  infra/      # leitura das planilhas (openpyxl) e escrita dos resultados
  services/   # regras de negócio: normalização de nomes + construção do De-Para
  config.py   # fontes, colunas e vocabulário de normalização
  errors.py   # exceções de domínio (a app não quebra com erro esperado)
scripts/      # entrypoints (build_depara)
web/          # frontend: HTML + CSS + JS separados (ECharts via CDN, ícones SVG)
tests/        # testes unittest (normalização, De-Para, leitura + erros)
data/         # saída gerada: depara.json (frontend) e depara.csv (conferência)
```

## Como rodar
** Opção A — só usar o que já está rodando. Abre no navegador:
### start http://localhost:8756/web/

** Opção B — derrubar o servidor antigo e subir limpo (útil se você mexeu no código e quer garantir estado novo):
### taskkill /PID 35604 /F
Depois, da raiz do projeto:

`` python -m http.server 8756
  e abra http://localhost:8756/web/.
``
Se as mudanças que você quer me mostrar são nas planilhas (subiu .xlsx novos), aí precisa regerar os dados antes — reprocessa tudo com:

### python -m scripts.build_tudo

### Atualizar com planilhas novas

1. Substitua os `.xlsx` na raiz do projeto pelos novos, **mantendo os mesmos
   nomes de arquivo** (ver "Fontes de dados").
2. Rode o pipeline inteiro de uma vez:

```bash
python -m scripts.build_tudo
```

Esse comando roda os cinco passos na ordem (De-Para → Fatos → Métricas →
Impacto → Dashboard), cada um lendo a saída do anterior, e para na primeira
falha. Se preferir passo a passo:

```bash
python -m scripts.build_depara
python -m scripts.build_fatos
python -m scripts.build_metricas
python -m scripts.build_impacto
python -m scripts.build_dashboard
```

> A coluna de **eficiência oficial** é localizada pelo **rótulo do cabeçalho**
> ("% 4WK" no jeans, "MÉDIA 4W" no não-jeans), não por posição fixa — assim a
> planilha pode ganhar colunas de semana sem quebrar a leitura. Se o rótulo
> mudar, o build falha com uma mensagem clara em vez de ler a coluna errada.

Servir a aplicação (a partir da raiz do projeto) e abrir `/web/` — o dashboard
abre no Ranking; a página do De-Para fica em `/web/depara.html`:

```bash
python -m http.server 8756
```

Rodar os testes:

```bash
python -m unittest discover -s tests -v
```

## Aba Qualidade (nota, 2ª qualidade e causas)

Quarta aba do mesmo dashboard, com as três análises da aba GRÁFICOS do
`Indicador geral`:

- **Nota de Qualidade** — índice de demérito ponderado (maior = pior):
  `0,6 × %Reprovado + 0,3 × %Aprovado com Concessão + 0,1 × (Σ 2QA ÷ Σ Produção)`.
- **2ª Qualidade** — `Σ 2QA ÷ Σ Produção` por oficina.
- **Principais Causas** — soma de peças por defeito, inspeção de 2ª qualidade,
  setor de costura.

Dados: `python -m scripts.build_qualidade` lê as abas **RESUMO** e **DEFEITOS**
e grava `data/qualidade.json` (compacto). Também roda dentro de
`python -m scripts.build_tudo` (passo 6/6). Só o JSON agregado é publicado — a
planilha de 24 MB nunca sobe (ver `.gitignore`).

## Hospedagem no Streamlit Cloud

`streamlit_app.py` embute a **mesma SPA** (HTML/CSS/JS + ECharts) num iframe,
injetando `data/*.json` no HTML. Na barra lateral há a área de **upload das
planilhas** e o botão **Atualizar dados**, que roda o build e regenera os JSONs.

```bash
streamlit run streamlit_app.py
```

No Streamlit Cloud: aponte o app para `streamlit_app.py` (deps em
`requirements.txt`). O disco é efêmero — o botão atualiza a sessão atual; para
valer para todos e persistir, faça commit dos `data/*.json` regerados.

## Regras do De-Para (resumo)

- **Normalização**: caixa-alta, remoção de acentos e pontuação; separação de
  tokens de unidade/linha (`POLO`, `CARGO`, `MATRIZ`…) e de natureza jurídica
  (`LTDA`, `ME`…), preservando a unidade como atributo da variante.
- **Agrupamento**: **apenas pelo nome** — variantes com o mesmo nome-base formam
  uma única oficina. O CNPJ não é usado (nem lido) no De-Para.
- **Revisão humana**: sinaliza nomes-base quase idênticos (possíveis duplicatas
  a decidir manualmente, ex.: `...SOUSA` vs `...SOUZA`).

## Fontes de dados

A planilha `Indicador geral_Junho.xlsx` é intencionalmente ignorada.
Em `ESTOQUE OFICINAS - JEANS` e `ESTOQUE OFICINA NÃO JEANS` só as abas de
estoque/AUX são usadas. Detalhe das colunas em `app_oficinas/config.py`.

> **Cobertura temporal**: a produção (RECEBIMENTO) começa em jan/2026. As telas
> de métricas (fases seguintes) exibirão **alerta de dados ausentes** ao comparar
> períodos sem registro.
