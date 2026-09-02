"""Shell Streamlit para hospedar o Radar de Oficinas no Streamlit Cloud.

NÃO reimplementa a interface: embute a MESMA SPA de ``web/`` (HTML/CSS/JS +
ECharts) num iframe, injetando os dados de ``data/*.json`` direto no HTML (para
não depender de fetch relativo dentro do iframe). Assim o visual e as
tecnologias são idênticos aos do dashboard servido por ``http.server``.

Acrescenta só o que o Streamlit Cloud precisa: uma área na barra lateral onde a
equipe **sobe as planilhas** e, ao clicar em **Atualizar dados**, o pipeline de
build roda e regenera os JSONs — a página recarrega já com os números novos.

    streamlit run streamlit_app.py

Observação (Streamlit Cloud): o disco é efêmero. O botão atualiza os dados na
sessão atual; para a atualização valer para todos e persistir entre reinícios,
faça commit dos ``data/*.json`` regerados (arquivos pequenos).
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app_oficinas import config

RAIZ = Path(__file__).resolve().parent
WEB = RAIZ / "web"
DATA = RAIZ / "data"
EXPLICACAO = RAIZ / "docs" / "explicacao_oficinas.html"

st.set_page_config(page_title="Radar de Oficinas", layout="wide",
                   initial_sidebar_state="expanded")


def _ler(caminho: Path, padrao: str = "null") -> str:
    try:
        return caminho.read_text(encoding="utf-8")
    except OSError:
        return padrao


def montar_html() -> str:
    """Inlina index.html + CSS + JS e injeta os dados como variáveis globais."""
    html = _ler(WEB / "index.html")
    css_estilo = _ler(WEB / "assets/css/estilo.css", "")
    css_dash = _ler(WEB / "assets/css/dashboard.css", "")
    js_graf = _ler(WEB / "assets/js/graficos_dashboard.js", "")
    js_dash = _ler(WEB / "assets/js/dashboard.js", "")
    dashboard_json = _ler(DATA / "dashboard.json", "null")
    qualidade_json = _ler(DATA / "qualidade.json", "null")

    # Troca os <link>/<script> locais (com ?v=) pelo conteúdo embutido. O CDN do
    # ECharts e as Google Fonts continuam como estão (carregam no iframe).
    import re
    html = re.sub(r'<link rel="stylesheet" href="assets/css/estilo\.css[^"]*">',
                  f"<style>{css_estilo}</style>", html)
    html = re.sub(r'<link rel="stylesheet" href="assets/css/dashboard\.css[^"]*">',
                  f"<style>{css_dash}</style>", html)
    # Injeta os dados ANTES dos scripts do app (dashboard.js os lê no load).
    injecao = (f"<script>window.__DASHBOARD__={dashboard_json};"
               f"window.__QUALIDADE__={qualidade_json};</script>")
    html = re.sub(r'<script src="assets/js/graficos_dashboard\.js[^"]*"></script>',
                  injecao + f"<script>{js_graf}</script>", html)
    html = re.sub(r'<script src="assets/js/dashboard\.js[^"]*"></script>',
                  f"<script>{js_dash}</script>", html)
    # Fixa o tema PRÓPRIO da SPA no embed — sem isso o iframe herda o
    # prefers-color-scheme do ambiente Streamlit e o dashboard "pega" o tema
    # errado. O botão de tema da própria SPA continua funcionando.
    html = html.replace('<html lang="pt-BR">', '<html lang="pt-BR" data-theme="dark">')
    return html


def montar_explicacao() -> str:
    """HTML da explicação por oficina (docs/), com aviso amigável se ausente.

    O arquivo é gerado pelo pipeline (passo 7) a cada "Atualizar dados"; num
    ambiente recém-implantado que ainda não regerou, mostra uma orientação em vez
    de quebrar.
    """
    padrao = ("<div style='padding:24px;font:15px system-ui;color:#e6edf3;"
              "background:#0f141b'>A explicação ainda não foi gerada. Clique em "
              "<b>Atualizar dados</b> para criá-la a partir das planilhas.</div>")
    return _ler(EXPLICACAO, padrao)


def _salvar_uploads(uploads) -> list[str]:
    # Salva na MESMA pasta de onde o pipeline lê (config.PLANILHAS_DIR). Antes
    # gravava na raiz enquanto a leitura passou a ser feita em Planilhas/, então
    # o upload nunca chegava ao build — o app dizia "sincronizado" sem mudar nada.
    #
    # Cada upload é salvo com o NOME CANÔNICO que o pipeline procura (mapeado por
    # palavras-chave). Assim o usuário pode subir "estoque jeans agosto.xlsx" ou
    # "Indicador geral_Julho.xlsx" que o build ainda encontra a base — sem isso, o
    # nome com ano/mês/acento diferente faria a base "sumir" e os valores não
    # mudariam. Se não casar nenhuma regra, mantém o nome original (não perde o
    # arquivo) e ele aparecerá como base faltante no aviso pós-build.
    destino = config.PLANILHAS_DIR
    destino.mkdir(parents=True, exist_ok=True)
    nomes = []
    for up in uploads:
        canonico = config.nome_canonico_upload(up.name)
        (destino / (canonico or up.name)).write_bytes(up.getbuffer())
        nomes.append(canonico or up.name)
    return nomes


def _bases_presentes() -> tuple[list[str], list[str]]:
    """Divide as planilhas esperadas em (presentes, faltando) em PLANILHAS_DIR."""
    presentes, faltando = [], []
    for arq in config.ARQUIVOS_ESPERADOS:
        (presentes if (config.PLANILHAS_DIR / arq).exists() else faltando).append(arq)
    return presentes, faltando


# Pistas do log, da MAIS específica para a mais genérica. A ordem é o que
# importa: o pipeline termina sempre com "FALHOU em '1/7 ...'. Abortando o
# restante." — uma linha que só diz ONDE parou. A causa real ("Aba 'Dados' não
# existe em postos.xlsx") vem antes. Varrer o log de trás para frente pegava a
# genérica e escondia a útil, deixando o usuário sem saber o que corrigir.
_PISTAS_MOTIVO: tuple[tuple[str, ...], ...] = (
    ("Planilha não encontrada", "Falha ao abrir a planilha"),
    ("Aba '", "Coluna", "cabeçalho"),
    ("não encontrada", "não existe", "faltam"),
    ("ERRO", "FALHOU"),
)


def _ultimo_motivo(log: str) -> str:
    """Extrai a linha de erro mais útil do log do build (motivo p/ o usuário)."""
    linhas = [l.strip() for l in log.splitlines() if l.strip()]
    for pistas in _PISTAS_MOTIVO:
        for linha in linhas:
            if any(p in linha for p in pistas):
                return linha
    return "verifique se todas as planilhas foram enviadas com os nomes esperados"


def _rodar_build() -> tuple[bool, str]:
    """Roda o pipeline completo; se ele falhar, cai para Qualidade-só.

    IMPORTANTE: ``build_tudo.main()`` NÃO levanta exceção quando um passo falha —
    ele engole o ``RadarError`` e devolve o código de saída ``1``. Antes este
    método só tratava exceções e ignorava esse código, então um build que falhou
    (planilha faltando/renomeada) era relatado como sucesso e os JSONs nunca eram
    regerados: a origem do "sincronizado mas sem mudança nos valores". Agora o
    código de saída é conferido de verdade.
    """
    import io
    from contextlib import redirect_stderr, redirect_stdout

    from app_oficinas.errors import RadarError
    from scripts import build_qualidade, build_tudo

    log = io.StringIO()
    with redirect_stdout(log), redirect_stderr(log):
        codigo = build_tudo.main()
    if codigo == 0:
        return True, "Pipeline completo atualizado (Ranking, Ficha, Impacto e Qualidade)."

    # Pipeline completo falhou. Tenta ao menos regerar a Qualidade, que só
    # depende do "Indicador geral".
    motivo = _ultimo_motivo(log.getvalue())
    try:
        with redirect_stdout(log), redirect_stderr(log):
            build_qualidade.main()
    except RadarError as erro2:
        return False, (f"Falha ao atualizar — nada foi alterado. Motivo: {motivo}. "
                       f"(Qualidade também falhou: {erro2}.) Reenvie as planilhas "
                       f"com os nomes esperados e tente de novo.")
    return True, (f"Apenas a Qualidade foi atualizada. O restante do dashboard NÃO "
                  f"mudou porque o pipeline completo falhou: {motivo}. Confira se "
                  f"TODAS as planilhas necessárias foram enviadas com os nomes "
                  f"corretos e atualize de novo.")


def _commitar_dados(arquivos: list[str]) -> tuple[bool, str]:
    """Commita os JSONs no GitHub (persistência entre reinícios do Cloud).

    Exige em .streamlit/secrets.toml (ou nos Secrets do Streamlit Cloud):
        [github]
        token = "ghp_..."      # token com permissão de escrita no repo
        repo = "usuario/APP_PERFOR"
        branch = "main"        # opcional (padrão: main)
    """
    import base64
    try:
        import requests
    except ImportError:
        return False, "Biblioteca 'requests' ausente (adicione ao requirements.txt)."
    try:
        gh = st.secrets["github"]
        token, repo = gh["token"], gh["repo"]
    except Exception:
        return False, ("Commit ignorado: configure os Secrets [github] token/repo "
                       "no Streamlit Cloud para persistir os dados.")
    branch = gh.get("branch", "main")
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json"}
    linhas = []
    falhou = False
    for rel in arquivos:
        caminho = RAIZ / rel
        if not caminho.exists():
            continue
        url = f"https://api.github.com/repos/{repo}/contents/{rel}"
        r = requests.get(url, headers=headers, params={"ref": branch}, timeout=30)
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {"message": f"Atualiza {rel} via app",
                   "content": base64.b64encode(caminho.read_bytes()).decode(),
                   "branch": branch}
        if sha:
            payload["sha"] = sha
        pr = requests.put(url, headers=headers, json=payload, timeout=30)
        ok_arquivo = pr.status_code in (200, 201)
        falhou = falhou or not ok_arquivo
        linhas.append(f"{rel}: {'ok' if ok_arquivo else 'erro ' + str(pr.status_code)}")
    # Nunca relatar sucesso quando o PUT falhou (ex.: 403 = token sem permissão
    # 'Contents: Read and write') — senão o app mostraria "publicado" e os dados
    # não teriam persistido no repositório.
    if falhou:
        return False, ("Falha ao publicar no GitHub (" + "; ".join(linhas) +
                       "). Erro 403 = o token não tem permissão 'Contents: "
                       "Read and write' neste repositório.")
    return True, "Commit no GitHub — " + "; ".join(linhas)


# --------------------------------------------------------------- barra lateral
# Deixa o embed no comando visual: some com o chrome do Streamlit (menu/rodapé)
# e cola o iframe no topo, sem margens.
st.markdown("""
<style>
  /* Some com o chrome do Streamlit (menu/deploy/rodapé), MAS mantém acessível o
     botão que reabre a barra lateral. O antigo "header{display:none}" escondia
     junto o botão de expandir (ele vive DENTRO do header): ao recolher a barra
     — o que acontece sozinho no celular e na Streamlit Cloud — a área
     "Atualizar dados" sumia sem nenhuma forma de trazê-la de volta. */
  header[data-testid="stHeader"]{
    background:transparent !important; height:0 !important; min-height:0 !important;
    pointer-events:none;
  }
  #MainMenu, footer,
  header[data-testid="stHeader"] [data-testid="stMainMenu"],
  header[data-testid="stHeader"] [data-testid="stAppDeployButton"]{display:none !important;}
  /* Botão de reabrir a barra lateral: sempre visível e clicável. */
  [data-testid="stExpandSidebarButton"]{
    display:inline-flex !important; visibility:visible !important; pointer-events:auto !important;
  }
  /* Botão de recolher (dentro da barra) sempre visível, não só no hover. */
  [data-testid="stSidebarCollapseButton"]{visibility:visible !important;}
  .block-container{padding:0 !important; max-width:100% !important;}
  section.main > div{gap:0 !important;}
  div[data-testid="stSidebarUserContent"]{padding-top:1rem;}
</style>
""", unsafe_allow_html=True)

st.sidebar.header("Atualizar dados")
uploads = st.sidebar.file_uploader(
    "Planilhas (.xlsx)", type=["xlsx"], accept_multiple_files=True)

# Resultado da última atualização — guardado em session_state para sobreviver ao
# st.rerun() (que recarrega o dashboard com os números novos). Sem isso, a
# mensagem sumiria antes de o usuário lê-la.
_aviso = st.session_state.pop("_aviso_atualizacao", None)
if _aviso:
    getattr(st.sidebar, _aviso[0])(_aviso[1])

if st.sidebar.button("Atualizar dados", type="primary", use_container_width=True):
    if not uploads:
        st.sidebar.warning("Selecione ao menos uma planilha.")
    else:
        with st.spinner("Processando..."):
            _salvar_uploads(uploads)
            ok, msg = _rodar_build()
        # Bases que ainda faltam para o pipeline COMPLETO (Ranking/Ficha/Impacto).
        # Pode subir uma planilha por vez: elas se acumulam no disco da sessão e o
        # dashboard só regenera quando TODAS estão presentes.
        _, faltando = _bases_presentes()
        if ok:
            with st.spinner("Publicando no GitHub..."):
                cok, cmsg = _commitar_dados([
                    "data/dashboard.json", "data/qualidade.json",
                    "docs/explicacao_oficinas.html",
                ])
            extra = ""
            if faltando:
                extra = (" Para o dashboard completo, ainda faltam: "
                         + "; ".join(faltando) + ".")
            # success (verde) só quando o commit também passou; senão warning
            # (amarelo) deixando claro que atualizou na sessão mas NÃO persistiu.
            st.session_state["_aviso_atualizacao"] = (
                "success" if cok else "warning", f"{msg}{extra} {cmsg}")
            st.rerun()
        elif faltando:
            # Nada regerou ainda, mas é só acúmulo incremental (faltam bases). Sem
            # alarde: orienta o próximo envio em vez de mostrar erro vermelho.
            st.sidebar.info(
                "Recebido. Para gerar o dashboard, ainda faltam estas bases: "
                + "; ".join(faltando)
                + ". Envie-as (juntas ou uma a uma) e clique em Atualizar de novo. "
                + "A Qualidade precisa só do 'Indicador geral'.")
        else:
            # Todas as bases presentes, mas o build falhou mesmo assim: erro real
            # (planilha corrompida, aba/coluna faltando). Mostra o motivo.
            st.sidebar.error(msg)

# --------------------------------------------------------------------- exibição
# Seletor de visão: o Dashboard (SPA) ou a Explicação por oficina (docs/). No
# Streamlit Cloud não há servidor de estáticos para abrir o .html por link, então
# a explicação é renderizada aqui mesmo, no lugar do dashboard.
st.sidebar.markdown("---")
visao = st.sidebar.radio(
    "Exibir", ["Dashboard", "Explicação por oficina"],
    help="A Explicação mostra o COMO e o PORQUÊ de cada resultado de cada oficina.")

if visao == "Explicação por oficina":
    components.html(montar_explicacao(), height=2400, scrolling=True)
else:
    components.html(montar_html(), height=2400, scrolling=True)
