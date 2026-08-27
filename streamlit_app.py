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


def _salvar_uploads(uploads) -> list[str]:
    nomes = []
    esperado = config.QUALIDADE_RESUMO.arquivo
    for up in uploads:
        (RAIZ / up.name).write_bytes(up.getbuffer())
        nomes.append(up.name)
        # Garante o nome que o config espera para a planilha de qualidade.
        if "indicador" in up.name.lower() and up.name != esperado:
            (RAIZ / esperado).write_bytes(up.getbuffer())
    return nomes


def _rodar_build() -> tuple[bool, str]:
    """Roda o pipeline completo; se faltar alguma planilha, cai para Qualidade."""
    from app_oficinas.errors import RadarError
    from scripts import build_qualidade, build_tudo
    try:
        build_tudo.main()
        return True, "Pipeline completo atualizado (Ranking, Ficha, Impacto e Qualidade)."
    except RadarError as erro:
        try:
            build_qualidade.main()
            return True, (f"Qualidade atualizada. O restante do dashboard não pôde "
                          f"ser regerado (faltou uma planilha): {erro}")
        except RadarError as erro2:
            return False, f"Falha ao atualizar: {erro2}"


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
        linhas.append(f"{rel}: {'ok' if pr.status_code in (200, 201) else 'erro ' + str(pr.status_code)}")
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

if st.sidebar.button("Atualizar dados", type="primary", use_container_width=True):
    if not uploads:
        st.sidebar.warning("Selecione ao menos uma planilha.")
    else:
        with st.spinner("Processando..."):
            _salvar_uploads(uploads)
            ok, msg = _rodar_build()
        if ok:
            st.sidebar.success(msg)
            with st.spinner("Publicando no GitHub..."):
                cok, cmsg = _commitar_dados(["data/dashboard.json", "data/qualidade.json"])
            (st.sidebar.success if cok else st.sidebar.info)(cmsg)
            st.rerun()
        else:
            st.sidebar.error(msg)

# ------------------------------------------------------------------- dashboard
components.html(montar_html(), height=2400, scrolling=True)
