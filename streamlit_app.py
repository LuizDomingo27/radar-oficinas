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

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app_oficinas import config
from app_oficinas.errors import RadarError
# O pipeline é importado AQUI, junto com o ``config``, de propósito.
#
# Antes ele era importado lá dentro de ``_rodar_build`` (só no 1º clique em
# "Atualizar dados"). No Streamlit Cloud o processo fica vivo por horas e o
# ``/mount/src`` é atualizado por trás (o próprio app comita os data/*.json e o
# Cloud faz o pull). Com o import tardio, o ``config`` já estava na memória com
# o código ANTIGO enquanto ``scripts``/``infra`` eram lidos do disco JÁ NOVO —
# metades de commits diferentes no mesmo processo. Foi assim que
# ``leitor_fatos.ler_faturamento`` (novo) morreu num ``config.FATURAMENTO``
# (atributo que só existe no config novo). Importando tudo no mesmo instante, o
# processo inteiro fica coerente com um único commit.
from scripts import build_qualidade, build_tudo

RAIZ = Path(__file__).resolve().parent
WEB = RAIZ / "web"
DATA = RAIZ / "data"

st.set_page_config(page_title="Radar de Oficinas", layout="wide",
                   initial_sidebar_state="collapsed")


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
    faturamento_json = _ler(DATA / "faturamento.json", "null")
    dividas_json = _ler(DATA / "dividas.json", "null")

    # Troca os <link>/<script> locais (com ?v=) pelo conteúdo embutido. O CDN do
    # ECharts e as Google Fonts continuam como estão (carregam no iframe).
    #
    # IMPORTANTE: a reposição vai como FUNÇÃO (lambda), não como string. Numa
    # string de reposição o re.sub interpreta escapes (``\d``, ``\n``, ``\g``…) e
    # o JS/CSS/JSON embutido contém essas sequências (ex.: regex ``/\d{4}/`` no
    # graficos_dashboard.js), o que quebrava o build com "bad escape". A função
    # devolve o texto literal, sem qualquer interpretação de escape.
    import re
    def troca(padrao: str, conteudo: str, alvo: str) -> str:
        return re.sub(padrao, lambda _m: conteudo, alvo)

    html = troca(r'<link rel="stylesheet" href="assets/css/estilo\.css[^"]*">',
                 f"<style>{css_estilo}</style>", html)
    html = troca(r'<link rel="stylesheet" href="assets/css/dashboard\.css[^"]*">',
                 f"<style>{css_dash}</style>", html)
    # Injeta os dados ANTES dos scripts do app (dashboard.js os lê no load).
    injecao = (f"<script>window.__DASHBOARD__={dashboard_json};"
               f"window.__QUALIDADE__={qualidade_json};"
               f"window.__FATURAMENTO__={faturamento_json};"
               f"window.__DIVIDAS__={dividas_json};</script>")
    html = troca(r'<script src="assets/js/graficos_dashboard\.js[^"]*"></script>',
                 injecao + f"<script>{js_graf}</script>", html)
    html = troca(r'<script src="assets/js/dashboard\.js[^"]*"></script>',
                 f"<script>{js_dash}</script>", html)
    # Fixa o tema PRÓPRIO da SPA no embed — sem isso o iframe herda o
    # prefers-color-scheme do ambiente Streamlit e o dashboard "pega" o tema
    # errado. O botão de tema da própria SPA continua funcionando.
    html = html.replace('<html lang="pt-BR">', '<html lang="pt-BR" data-theme="dark">')
    return html


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


def _canonicos_no_disco() -> set[str]:
    """Nomes canônicos das planilhas já salvas na pasta da sessão."""
    return {arq for arq in config.ARQUIVOS_ESPERADOS
            if (config.PLANILHAS_DIR / arq).exists()}


def _canonicos_selecionados(uploads) -> set[str]:
    """Nomes canônicos reconhecidos na seleção ATUAL do file_uploader.

    Mapeia cada arquivo escolhido pelo nome canônico (por palavras-chave), para
    a checklist já refletir o que está prestes a ser enviado — antes mesmo de
    clicar em "Atualizar dados". Arquivos que não casam nenhuma regra são
    ignorados aqui (aparecem à parte, como "não reconhecidos").
    """
    canonicos = set()
    for up in uploads or []:
        canonico = config.nome_canonico_upload(up.name)
        if canonico:
            canonicos.add(canonico)
    return canonicos


def _uploads_nao_reconhecidos(uploads) -> list[str]:
    """Nomes de arquivos selecionados que não casam nenhuma planilha esperada."""
    return [up.name for up in (uploads or [])
            if config.nome_canonico_upload(up.name) is None]


def _render_checklist(disponiveis: set[str]) -> None:
    """Desenha a checklist visual das planilhas: prontas x faltando.

    ``disponiveis`` = canônicos no disco ∪ selecionados agora. As que faltam
    ganham cor e ícone DIFERENTES (âmbar, contorno tracejado) para saltar aos
    olhos em meio às muitas bases. Renderizado com HTML/CSS inline (o embed já
    fixa tema escuro), sem depender de componentes extras do Streamlit.
    """
    situacao = config.situacao_planilhas(disponiveis)
    prontas = sum(1 for *_, ok in situacao if ok)
    total = len(situacao)
    itens = []
    for _arq, rotulo, ok in situacao:
        if ok:
            cor, borda, fundo, icone, estado = (
                "#22c55e", "#22c55e55", "#22c55e14", "✓", "pronta")
        else:
            cor, borda, fundo, icone, estado = (
                "#f59e0b", "#f59e0b", "#f59e0b1f", "!", "falta enviar")
        estilo_borda = "solid" if ok else "dashed"
        itens.append(
            f'<li style="display:flex;align-items:center;gap:.6rem;'
            f'padding:.55rem .8rem;border:1.5px {estilo_borda} {borda};'
            f'border-radius:.6rem;background:{fundo};">'
            f'<span style="flex:0 0 auto;width:1.5rem;height:1.5rem;'
            f'display:inline-flex;align-items:center;justify-content:center;'
            f'border-radius:50%;background:{cor};color:#0b0f19;font-weight:800;'
            f'font-size:.9rem;">{icone}</span>'
            f'<span style="flex:1 1 auto;color:#e5e7eb;font-weight:600;">{rotulo}'
            f'</span>'
            f'<span style="flex:0 0 auto;color:{cor};font-weight:700;'
            f'font-size:.8rem;text-transform:uppercase;letter-spacing:.03em;">'
            f'{estado}</span></li>')

    concluido = prontas == total
    cor_topo = "#22c55e" if concluido else "#f59e0b"
    resumo = ("Todas as planilhas prontas — pode atualizar."
              if concluido else f"Faltam {total - prontas} de {total} planilhas.")
    st.markdown(
        f'<div style="margin:.2rem 0 1rem;">'
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
        f'margin-bottom:.5rem;">'
        f'<strong style="color:#e5e7eb;">Planilhas necessárias</strong>'
        f'<span style="color:{cor_topo};font-weight:700;">{prontas}/{total} — {resumo}'
        f'</span></div>'
        f'<ul style="list-style:none;margin:0;padding:0;display:grid;gap:.4rem;">'
        + "".join(itens) + "</ul></div>",
        unsafe_allow_html=True)


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


def _falha_inesperada(erro: BaseException) -> str:
    """Mensagem para um erro que NÃO é ``RadarError`` (falha não prevista).

    ``RadarError`` é a família de problemas que o pipeline sabe explicar (aba
    renomeada, planilha ausente, coluna sumida) — esses viram texto de ajuda. O
    que sobra é defeito de código ou ambiente: em vez de derrubar a página com
    um traceback (e perder os uploads da sessão), devolvemos o tipo e a
    mensagem do erro, que é o que permite diagnosticar.

    ``AttributeError`` ganha uma dica extra: no Streamlit Cloud ele costuma
    significar que o processo está com módulos de commits diferentes (o
    ``/mount/src`` mudou embaixo do app já rodando). Reiniciar resolve.
    """
    detalhe = f"{type(erro).__name__}: {erro}"
    if isinstance(erro, AttributeError):
        return ("Falha inesperada ao atualizar — nada foi alterado. "
                f"Detalhe: {detalhe}. Isso costuma ser o app rodando com uma "
                "versão antiga do código em memória: reinicie a aplicação "
                "(Manage app › Reboot) e envie as planilhas de novo.")
    return ("Falha inesperada ao atualizar — nada foi alterado. "
            f"Detalhe: {detalhe}. Se persistir, reinicie a aplicação "
            "(Manage app › Reboot) e tente de novo.")


def _rodar_build() -> tuple[bool, str]:
    """Roda o pipeline completo; se ele falhar, cai para Qualidade-só.

    IMPORTANTE: ``build_tudo.main()`` NÃO levanta exceção quando um passo falha —
    ele engole o ``RadarError`` e devolve o código de saída ``1``. Antes este
    método só tratava exceções e ignorava esse código, então um build que falhou
    (planilha faltando/renomeada) era relatado como sucesso e os JSONs nunca eram
    regerados: a origem do "sincronizado mas sem mudança nos valores". Agora o
    código de saída é conferido de verdade.

    Nada que aconteça aqui pode derrubar a página: qualquer exceção fora da
    família ``RadarError`` vira mensagem (ver ``_falha_inesperada``). Um
    traceback na tela apagaria o resultado do upload e não diria ao usuário o
    que fazer.
    """
    log = io.StringIO()
    try:
        with redirect_stdout(log), redirect_stderr(log):
            codigo = build_tudo.main()
    except Exception as erro:  # noqa: BLE001 — o app não pode quebrar
        return False, _falha_inesperada(erro)
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
    except Exception as erro2:  # noqa: BLE001 — o app não pode quebrar
        return False, (f"Falha ao atualizar — nada foi alterado. Motivo: {motivo}. "
                       f"({_falha_inesperada(erro2)})")
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
        # A rede é a parte que mais falha e a que menos justifica derrubar a
        # página: os JSONs JÁ foram regerados em disco. Um timeout/DNS vira
        # linha de erro no relatório, com o app de pé.
        try:
            r = requests.get(url, headers=headers, params={"ref": branch}, timeout=30)
            sha = r.json().get("sha") if r.status_code == 200 else None
            payload = {"message": f"Atualiza {rel} via app",
                       "content": base64.b64encode(caminho.read_bytes()).decode(),
                       "branch": branch}
            if sha:
                payload["sha"] = sha
            pr = requests.put(url, headers=headers, json=payload, timeout=30)
            ok_arquivo = pr.status_code in (200, 201)
            estado = "ok" if ok_arquivo else f"erro {pr.status_code}"
        except (requests.RequestException, OSError, ValueError) as erro:
            ok_arquivo = False
            estado = f"erro de rede ({type(erro).__name__})"
        falhou = falhou or not ok_arquivo
        linhas.append(f"{rel}: {estado}")
    # Nunca relatar sucesso quando o PUT falhou (ex.: 403 = token sem permissão
    # 'Contents: Read and write') — senão o app mostraria "publicado" e os dados
    # não teriam persistido no repositório.
    if falhou:
        return False, ("Falha ao publicar no GitHub (" + "; ".join(linhas) +
                       "). Erro 403 = o token não tem permissão 'Contents: "
                       "Read and write' neste repositório.")
    return True, "Commit no GitHub — " + "; ".join(linhas)


# ------------------------------------------------------------ estilo do embed
# Deixa o embed no comando visual: some com o chrome do Streamlit (menu/rodapé)
# e cola o iframe no topo, sem margens. A barra lateral foi REMOVIDA — a área
# "Atualizar dados" agora vive no fim da página (ver ``render_atualizacao``).
st.markdown("""
<style>
  /* Some com o chrome do Streamlit (menu/deploy/rodapé) e cola o iframe no
     topo, sem margens. */
  header[data-testid="stHeader"]{
    background:transparent !important; height:0 !important; min-height:0 !important;
    pointer-events:none;
  }
  #MainMenu, footer,
  header[data-testid="stHeader"] [data-testid="stMainMenu"],
  header[data-testid="stHeader"] [data-testid="stAppDeployButton"]{display:none !important;}
  /* Sidebar removida: nada mais é renderizado nela. Esconde a barra e qualquer
     botão que a reabriria, para não deixar controle órfão na tela. */
  [data-testid="stSidebar"],
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="stExpandSidebarButton"]{display:none !important;}
  .block-container{padding:0 !important; max-width:100% !important;}
  section.main > div{gap:0 !important;}
</style>
""", unsafe_allow_html=True)


def render_atualizacao() -> None:
    """Área de upload das planilhas + botão "Atualizar dados", NO FIM da página.

    Antes ficava na barra lateral; agora é renderizada logo abaixo do dashboard
    (que abre na aba Ranking), como pedido. É Streamlit puro — NÃO roda dentro
    do iframe da SPA: sobe as planilhas, dispara o pipeline de build e recarrega
    a página já com os números novos.

    O bloco é envolto por colunas de folga (``_esq``/``_dir``) só para dar
    respiro lateral sem tirar o full-bleed do iframe acima.
    """
    st.divider()
    _esq, meio, _dir = st.columns([1, 30, 1])
    with meio:
        st.subheader("Atualizar dados")

        # Resultado da última atualização — guardado em session_state para
        # sobreviver ao st.rerun() (que recarrega o dashboard com os números
        # novos). Sem isso, a mensagem sumiria antes de o usuário lê-la.
        _aviso = st.session_state.pop("_aviso_atualizacao", None)
        if _aviso:
            getattr(st, _aviso[0])(_aviso[1])

        st.caption(
            "Envie as planilhas .xlsx abaixo. Pode subir todas de uma vez ou "
            "uma a uma — elas se acumulam na sessão. O nome do arquivo é "
            "reconhecido automaticamente (ano/mês/acento diferentes não "
            "atrapalham). Acompanhe pela checklist o que ainda falta.")

        uploads = st.file_uploader(
            "Planilhas (.xlsx)", type=["xlsx"], accept_multiple_files=True)

        # Checklist AO VIVO: já refletindo o que está no disco da sessão + o que
        # acabou de ser selecionado no uploader (o Streamlit re-executa a cada
        # arquivo escolhido). As bases faltando aparecem em cor/ícone distintos.
        disponiveis = _canonicos_no_disco() | _canonicos_selecionados(uploads)
        _render_checklist(disponiveis)

        nao_reconhecidos = _uploads_nao_reconhecidos(uploads)
        if nao_reconhecidos:
            st.warning(
                "Não reconheci estes arquivos como uma das planilhas esperadas "
                "(confira o nome): " + "; ".join(nao_reconhecidos))

        if st.button("Atualizar dados", type="primary"):
            if not uploads:
                st.warning("Selecione ao menos uma planilha.")
            else:
                with st.spinner("Processando..."):
                    _salvar_uploads(uploads)
                    ok, msg = _rodar_build()
                # Bases que ainda faltam para o pipeline COMPLETO
                # (Ranking/Ficha/Impacto). Pode subir uma planilha por vez: elas
                # se acumulam no disco da sessão e o dashboard só regenera quando
                # TODAS estão presentes.
                _, faltando = _bases_presentes()
                if ok:
                    with st.spinner("Publicando no GitHub..."):
                        cok, cmsg = _commitar_dados([
                            "data/dashboard.json", "data/qualidade.json",
                            "data/faturamento.json", "data/dividas.json",
                        ])
                    extra = ""
                    if faltando:
                        extra = (" Para o dashboard completo, ainda faltam: "
                                 + "; ".join(faltando) + ".")
                    # success (verde) só quando o commit também passou; senão
                    # warning (amarelo) deixando claro que atualizou na sessão
                    # mas NÃO persistiu.
                    st.session_state["_aviso_atualizacao"] = (
                        "success" if cok else "warning", f"{msg}{extra} {cmsg}")
                    st.rerun()
                elif faltando:
                    # Nada regerou ainda, mas é só acúmulo incremental (faltam
                    # bases). Sem alarde: orienta o próximo envio em vez de erro.
                    st.info(
                        "Recebido. Para gerar o dashboard, ainda faltam estas "
                        "bases: " + "; ".join(faltando)
                        + ". Envie-as (juntas ou uma a uma) e clique em Atualizar "
                        + "de novo. A Qualidade precisa só do 'Indicador geral'.")
                else:
                    # Todas as bases presentes, mas o build falhou mesmo assim:
                    # erro real (planilha corrompida, aba/coluna faltando).
                    st.error(msg)


# --------------------------------------------------------------------- exibição
# Blindagem (regra do AGENTS.md: o app não pode quebrar). Qualquer falha ao
# montar ou renderizar a SPA exibe uma mensagem clara — o QUÊ e ONDE ocorreu —
# em vez de derrubar a página inteira com um traceback.
try:
    _html_painel = montar_html()
except Exception as exc:  # captura ampla proposital: é a última linha de defesa
    st.error(
        "Não foi possível montar o painel — etapa: montar_html "
        "(inlining de HTML/CSS/JS e injeção dos dados de data/*.json). "
        f"Detalhe: {type(exc).__name__}: {exc}")
    st.info("A barra lateral continua ativa para reenviar planilhas e atualizar. "
            "Se o erro persistir, confira data/dashboard.json e os arquivos em web/.")
else:
    try:
        components.html(_html_painel, height=2400, scrolling=True)
    except Exception as exc:  # falha na renderização do iframe
        st.error(
            "Falha ao renderizar o painel no navegador — etapa: components.html. "
            f"Detalhe: {type(exc).__name__}: {exc}")

# Área de upload/atualização no FIM da página (abaixo do dashboard). Fica fora
# do try/except da exibição de propósito: mesmo que a SPA não monte, a equipe
# ainda precisa poder reenviar planilhas e atualizar os dados.
render_atualizacao()
