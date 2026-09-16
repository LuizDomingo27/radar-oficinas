"""
ui/cadastro_view.py
--------------------
Camada de visualização (UI) separada para a funcionalidade de cadastro
de dados (manual e importação em lote).

Persistência: os lançamentos são gravados diretamente na tabela `postos` do
Neon (Postgres gerenciado) — persistência real, sem o workaround de
sincronizar um arquivo local com o GitHub que era necessário no SQLite.
"""

from __future__ import annotations

import datetime
import pandas as pd
import streamlit as st

from app_postos.core.config import Columns
from app_postos.core.errors import error_boundary
from app_postos.core.record import RecordValidationError, validate_record_fields
from app_postos.services.data_writer import insert_record, insert_bulk_records, check_record_exists
from app_postos.services.record_service import (
    RecordDuplicateError,
    RecordNotFoundError,
    list_records,
    update_record,
)


@st.dialog("Confirmar Lançamento com Valores Zerados")
def confirm_zero_dialog(record_data: dict) -> None:
    st.warning(
        "Os seguintes indicadores foram informados com valor **zero (0)**. "
        "Por favor, confirme se deseja prosseguir:"
    )

    # Lista os campos zerados
    zeros = []
    if record_data["qtd_efetivos"] == 0:
        zeros.append("- **QTD Efetivos (Planejado)**")
    if record_data["qtd_trabalhados"] == 0:
        zeros.append("- **QTD Trabalhados (Realizado)**")
    if record_data["contratacoes"] == 0:
        zeros.append("- **Contratações**")
    if record_data["demissoes"] == 0:
        zeros.append("- **Demissões**")

    for z in zeros:
        st.markdown(z)

    st.markdown("<br>", unsafe_allow_html=True)
    st.write(
        f"**Registro:** Oficina `{record_data['oficina']}` · "
        f"MP `{record_data['mp']}` · Semana `{record_data['semana']}`"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sim, salvar mesmo assim", use_container_width=True):
            with error_boundary("salvar o registro"):
                insert_record(
                    frete=record_data["frete"],
                    mp=record_data["mp"],
                    oficina=record_data["oficina"],
                    data_efetivos=record_data["data_efetivos"],
                    qtd_efetivos=record_data["qtd_efetivos"],
                    data_trabalhados=record_data["data_trabalhados"],
                    qtd_trabalhados=record_data["qtd_trabalhados"],
                    contratacoes=record_data["contratacoes"],
                    demissoes=record_data["demissoes"],
                    semana=record_data["semana"],
                )
                st.cache_data.clear()
                st.success("Registro salvo com sucesso!")
                st.rerun()
    with col2:
        if st.button("Não, voltar e ajustar", use_container_width=True):
            st.rerun()


@st.dialog("Confirmar Sobrescrita do Registro")
def confirm_overwrite_dialog(record_id: int, record_data: dict) -> None:
    """
    Diálogo de confirmação da EDIÇÃO. Deixa explícito que salvar substitui
    (sobrescreve) o registro atual de forma permanente antes de gravar.
    """
    st.warning(
        "**Atenção:** ao confirmar, os dados atuais deste registro serão "
        "**sobrescritos permanentemente** pelos novos valores. Esta ação não "
        "pode ser desfeita."
    )
    st.write(
        f"**Registro #{record_id}** · Oficina `{record_data['oficina']}` · "
        f"MP `{record_data['mp']}` · Semana `{record_data['semana']}`"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sim, sobrescrever", use_container_width=True, type="primary"):
            with error_boundary("atualizar o registro"):
                try:
                    update_record(record_id, **record_data)
                except RecordValidationError as exc:
                    for msg in exc.errors:
                        st.error(msg)
                    return
                except RecordDuplicateError as exc:
                    st.error(f"**Erro de Duplicidade:** {exc}")
                    return
                except RecordNotFoundError:
                    st.error(
                        "Este registro não foi encontrado (pode ter sido removido). "
                        "Recarregue a página e tente novamente."
                    )
                    return
                st.cache_data.clear()
                st.success(
                    "Registro atualizado com sucesso! Os novos dados já refletem no Dashboard."
                )
                st.rerun()
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()


def render_cadastro_page(df_full: pd.DataFrame) -> None:
    """Renderiza a página de inserção de novos registros e importação em lote."""
    st.markdown(
        """
        <div class="app-header">
            <div class="title-row">
                <h1>Lançamento de Dados</h1>
            </div>
            <div class="subtitle">Adicione novos registros manuais ou importe arquivos Excel para o banco de dados</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_manual, tab_editar, tab_lote = st.tabs(
        ["Formulário Manual", "Editar Registro", "Importação em Lote"]
    )

    # Extrai opções únicas atuais para facilitar a seleção e evitar typos
    frete_options = sorted(df_full[Columns.FRETE].dropna().unique().tolist())
    mp_options = sorted(df_full[Columns.MP].dropna().unique().tolist())

    # Extrai a oficina sem a matéria-prima (coluna original)
    oficina_options = sorted(df_full[Columns.OFICINA].dropna().unique().tolist())

    with tab_manual:
        _render_manual_form(frete_options, mp_options, oficina_options)

    with tab_editar:
        _render_edit_form()

    with tab_lote:
        _render_bulk_import()


def _render_manual_form(
    frete_options: list[str], mp_options: list[str], oficina_options: list[str]
) -> None:
    with st.container(key="cadastro_manual_form"):
        st.markdown("##### Novo Registro")
        st.caption("Preencha as informações abaixo para gravar um novo registro no banco de dados.")

        # ── Seção 1: Identificação ────────────────────────────────────────
        with st.container(border=True):
            st.markdown(
                """
                <div class="form-section-hdr">
                    <span class="fsh-num">01</span>
                    <span class="fsh-title">Identificação</span>
                    <span class="fsh-hint">Oficina · Matéria-prima · Transportador</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Renderiza os inputs diretamente (sem st.form) para habilitar re-execução
            # instantânea na mudança dos selectboxes ("Outro...").
            col1, col2, col3 = st.columns(3)

            with col1:
                oficina_sel = st.selectbox(
                    "Oficina",
                    options=oficina_options + [" Outro... (Novo cadastro)"],
                    index=0,
                    help="Selecione uma oficina existente ou marque 'Outro...' para digitar uma nova."
                )
                nova_oficina = ""
                if oficina_sel == " Outro... (Novo cadastro)":
                    nova_oficina = st.text_input(
                        "Nome da Nova Oficina",
                        placeholder="Ex: OFICINA EXCELENCIA LTDA",
                        help="Digite o nome completo da nova oficina."
                    )

            with col2:
                mp_sel = st.selectbox(
                    "Matéria-prima (MP)",
                    options=mp_options + [" Outro... (Novo cadastro)"],
                    index=0,
                )
                nova_mp = ""
                if mp_sel == " Outro... (Novo cadastro)":
                    nova_mp = st.text_input(
                        "Nome da Nova MP",
                        placeholder="Ex: ALGODAO",
                    )

            with col3:
                frete_sel = st.selectbox(
                    "Frete (Transportador)",
                    options=frete_options + [" Outro... (Novo cadastro)"],
                    index=0,
                )
                novo_frete = ""
                if frete_sel == " Outro... (Novo cadastro)":
                    novo_frete = st.text_input(
                        "Nome do Novo Transportador",
                        placeholder="Ex: RAPIDO BRASIL",
                    )

        # ── Seção 2: Período e Semana ───────────────────────────────────────
        with st.container(border=True):
            st.markdown(
                """
                <div class="form-section-hdr">
                    <span class="fsh-num">02</span>
                    <span class="fsh-title">Período e Semana</span>
                    <span class="fsh-hint">Datas de referência · Semana calculada automaticamente</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_dt1, col_dt2, col_sem = st.columns([1.2, 1.2, 0.8])

            with col_dt1:
                data_efetivos = st.date_input(
                    "Data Efetivos (Planejado)",
                    value=datetime.date.today(),
                    help="Data de referência para a quantidade planejada de efetivos."
                )

            with col_dt2:
                mesma_data = st.checkbox("Mesma data para 'Trabalhados'", value=True)
                if mesma_data:
                    data_trabalhados = data_efetivos
                else:
                    data_trabalhados = st.date_input(
                        "Data Trabalhados (Realizado)",
                        value=data_efetivos,
                        help="Data de referência para a quantidade real de trabalhadores presentes."
                    )

            with col_sem:
                semana_calculada = data_efetivos.isocalendar()[1]
                semana = st.number_input(
                    "Semana",
                    min_value=1,
                    max_value=53,
                    value=semana_calculada,
                    step=1,
                    help="Calculado automaticamente com base na 'Data Efetivos', mas você pode ajustar se necessário."
                )

        # ── Seção 3: Quantidades ─────────────────────────────────────────────
        with st.container(border=True):
            st.markdown(
                """
                <div class="form-section-hdr">
                    <span class="fsh-num">03</span>
                    <span class="fsh-title">Quantidades</span>
                    <span class="fsh-hint">Efetivos planejados · Presença realizada · Movimentação</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_n1, col_n2, col_n3, col_n4 = st.columns(4)

            with col_n1:
                qtd_efetivos = st.number_input("QTD Efetivos", min_value=0, value=0, step=1, help="Planejado")
            with col_n2:
                qtd_trabalhados = st.number_input("QTD Trabalhados", min_value=0, value=0, step=1, help="Realizado")
            with col_n3:
                contratacoes = st.number_input("Contratações", min_value=0, value=0, step=1)
            with col_n4:
                demissoes = st.number_input("Demissões", min_value=0, value=0, step=1)

        st.markdown("<br>", unsafe_allow_html=True)
        btn_gravar = st.button("Gravar Registro", use_container_width=True, type="primary")

    if btn_gravar:
        # Resolve os valores selecionados (existentes ou novos)
        final_oficina = nova_oficina if oficina_sel == " Outro... (Novo cadastro)" else oficina_sel
        final_mp = nova_mp if mp_sel == " Outro... (Novo cadastro)" else mp_sel
        final_frete = novo_frete if frete_sel == " Outro... (Novo cadastro)" else frete_sel

        # Validações básicas de preenchimento
        erros = []
        if not final_oficina or final_oficina.strip() == "":
            erros.append("O campo 'Oficina' é obrigatório.")
        if not final_mp or final_mp.strip() == "":
            erros.append("O campo 'Matéria-prima (MP)' é obrigatório.")
        if not final_frete or final_frete.strip() == "":
            erros.append("O campo 'Frete' é obrigatório.")

        if erros:
            for erro in erros:
                st.error(erro)
        else:
            with error_boundary("validar e gravar o registro"):
                # 1. Validação de Duplicidade (Oficina + MP + Semana + Data Efetivos)
                if check_record_exists(
                    final_oficina, final_mp, semana, data_efetivos.strftime("%Y-%m-%d")
                ):
                    st.error(
                        f"**Erro de Duplicidade:** Já existe um lançamento para a Oficina "
                        f"**'{final_oficina}'** com a Matéria-prima **'{final_mp}'** na "
                        f"**Semana {semana}/{data_efetivos.year}**. É permitido apenas um "
                        f"lançamento por oficina/matéria-prima em cada semana, "
                        f"independentemente do dia informado."
                    )
                else:
                    # Prepara os dados para inserção ou diálogo
                    record_data = {
                        "frete": final_frete,
                        "mp": final_mp,
                        "oficina": final_oficina,
                        "data_efetivos": data_efetivos.strftime("%Y-%m-%d"),
                        "qtd_efetivos": int(qtd_efetivos),
                        "data_trabalhados": data_trabalhados.strftime("%Y-%m-%d"),
                        "qtd_trabalhados": int(qtd_trabalhados),
                        "contratacoes": int(contratacoes),
                        "demissoes": int(demissoes),
                        "semana": int(semana),
                    }

                    # 2. Validação de Valores Zerados
                    has_zeros = (
                        qtd_efetivos == 0 or
                        qtd_trabalhados == 0 or
                        contratacoes == 0 or
                        demissoes == 0
                    )

                    if has_zeros:
                        # Chama a janela de confirmação nativa
                        confirm_zero_dialog(record_data)
                    else:
                        # Gravação direta sem zeros
                        insert_record(
                            frete=record_data["frete"],
                            mp=record_data["mp"],
                            oficina=record_data["oficina"],
                            data_efetivos=record_data["data_efetivos"],
                            qtd_efetivos=record_data["qtd_efetivos"],
                            data_trabalhados=record_data["data_trabalhados"],
                            qtd_trabalhados=record_data["qtd_trabalhados"],
                            contratacoes=record_data["contratacoes"],
                            demissoes=record_data["demissoes"],
                            semana=record_data["semana"],
                        )
                        st.cache_data.clear()
                        st.success(
                            f"Sucesso! Registro gravado para a Oficina '{final_oficina}' "
                            f"(Semana {semana}). Os dados já foram computados no Dashboard!"
                        )
                        st.rerun()  # Força o reset dos campos limpando os inputs


def _parse_iso_date_or_today(value) -> datetime.date:
    """Converte uma data vinda do banco (str ISO / date) em `date`; hoje se inválida."""
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return datetime.date.today()


def _edit_record_label(registro: dict) -> str:
    """Rótulo legível de um registro na seleção de edição."""
    data = str(registro.get(Columns.DATA_EFETIVOS, ""))[:10]
    ano = data[:4]
    return (
        f"Semana {registro.get(Columns.SEMANA)}/{ano} · "
        f"{registro.get(Columns.MP)} · {data} · "
        f"Efet {registro.get(Columns.QTD_EFETIVOS)}/Trab {registro.get(Columns.QTD_TRABALHADOS)} "
        f"(#{registro.get('id')})"
    )


def _render_edit_form() -> None:
    """Seleção + edição de um registro existente, com confirmação de sobrescrita."""
    with st.container(key="cadastro_edit_form"):
        st.markdown("##### Editar Registro")
        st.caption(
            "Selecione um registro para corrigir dados digitados incorretamente. "
            "Ao salvar, os dados atuais serão **sobrescritos**."
        )

        with error_boundary("carregar os registros para edição"):
            registros = list_records()

        if not registros:
            st.info("Ainda não há registros cadastrados para editar.")
            return

        # ── Seleção do registro (filtro por Oficina → registro específico) ──
        with st.container(border=True):
            st.markdown(
                """
                <div class="form-section-hdr">
                    <span class="fsh-num">01</span>
                    <span class="fsh-title">Selecionar Registro</span>
                    <span class="fsh-hint">Filtre pela oficina e escolha o lançamento</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            oficinas = sorted(
                {str(r.get(Columns.OFICINA, "")).strip() for r in registros if r.get(Columns.OFICINA)}
            )
            col_f1, col_f2 = st.columns([1, 2])
            with col_f1:
                oficina_filtro = st.selectbox(
                    "Oficina", options=oficinas, key="edit_oficina_filtro"
                )

            registros_oficina = [
                r for r in registros
                if str(r.get(Columns.OFICINA, "")).strip() == oficina_filtro
            ]
            by_id = {int(r["id"]): r for r in registros_oficina}
            with col_f2:
                record_id = st.selectbox(
                    "Registro",
                    options=list(by_id.keys()),
                    format_func=lambda i: _edit_record_label(by_id[i]),
                    key=f"edit_registro_sel_{oficina_filtro}",
                )

        registro = by_id[record_id]

        st.info(
            f"Você está **editando o registro #{record_id}**. "
            "Altere os campos abaixo e clique em *Salvar alterações* — "
            "será pedida uma confirmação antes de sobrescrever."
        )

        # ── Campos editáveis (pré-preenchidos com os valores atuais) ────────
        with st.container(border=True):
            st.markdown(
                """
                <div class="form-section-hdr">
                    <span class="fsh-num">02</span>
                    <span class="fsh-title">Dados do Registro</span>
                    <span class="fsh-hint">Identificação · Período · Quantidades</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                oficina = st.text_input(
                    "Oficina",
                    value=str(registro.get(Columns.OFICINA, "")),
                    key=f"edit_of_{record_id}",
                )
            with col2:
                mp = st.text_input(
                    "Matéria-prima (MP)",
                    value=str(registro.get(Columns.MP, "")),
                    key=f"edit_mp_{record_id}",
                )
            with col3:
                frete = st.text_input(
                    "Frete (Transportador)",
                    value=str(registro.get(Columns.FRETE, "")),
                    key=f"edit_fr_{record_id}",
                )

            col_dt1, col_dt2, col_sem = st.columns([1.2, 1.2, 0.8])
            with col_dt1:
                data_efetivos = st.date_input(
                    "Data Efetivos (Planejado)",
                    value=_parse_iso_date_or_today(registro.get(Columns.DATA_EFETIVOS)),
                    key=f"edit_de_{record_id}",
                )
            with col_dt2:
                data_trabalhados = st.date_input(
                    "Data Trabalhados (Realizado)",
                    value=_parse_iso_date_or_today(registro.get(Columns.DATA_TRABALHADOS)),
                    key=f"edit_dt_{record_id}",
                )
            with col_sem:
                semana = st.number_input(
                    "Semana",
                    min_value=1,
                    max_value=53,
                    value=int(registro.get(Columns.SEMANA, 1) or 1),
                    step=1,
                    key=f"edit_sem_{record_id}",
                )

            col_n1, col_n2, col_n3, col_n4 = st.columns(4)
            with col_n1:
                qtd_efetivos = st.number_input(
                    "QTD Efetivos", min_value=0,
                    value=int(registro.get(Columns.QTD_EFETIVOS, 0) or 0),
                    step=1, key=f"edit_qe_{record_id}",
                )
            with col_n2:
                qtd_trabalhados = st.number_input(
                    "QTD Trabalhados", min_value=0,
                    value=int(registro.get(Columns.QTD_TRABALHADOS, 0) or 0),
                    step=1, key=f"edit_qt_{record_id}",
                )
            with col_n3:
                contratacoes = st.number_input(
                    "Contratações", min_value=0,
                    value=int(registro.get(Columns.CONTRATACOES, 0) or 0),
                    step=1, key=f"edit_ct_{record_id}",
                )
            with col_n4:
                demissoes = st.number_input(
                    "Demissões", min_value=0,
                    value=int(registro.get(Columns.DEMISSOES, 0) or 0),
                    step=1, key=f"edit_dm_{record_id}",
                )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_salvar = st.button(
            "Salvar alterações", use_container_width=True, type="primary", key="edit_salvar_btn"
        )

    if btn_salvar:
        record_data = {
            "frete": frete,
            "mp": mp,
            "oficina": oficina,
            "data_efetivos": data_efetivos.strftime("%Y-%m-%d"),
            "qtd_efetivos": int(qtd_efetivos),
            "data_trabalhados": data_trabalhados.strftime("%Y-%m-%d"),
            "qtd_trabalhados": int(qtd_trabalhados),
            "contratacoes": int(contratacoes),
            "demissoes": int(demissoes),
            "semana": int(semana),
        }

        # Feedback imediato de validação antes de abrir a confirmação.
        try:
            validate_record_fields(
                oficina=oficina, mp=mp, frete=frete,
                data_efetivos=record_data["data_efetivos"],
                qtd_efetivos=record_data["qtd_efetivos"],
                data_trabalhados=record_data["data_trabalhados"],
                qtd_trabalhados=record_data["qtd_trabalhados"],
                contratacoes=record_data["contratacoes"],
                demissoes=record_data["demissoes"],
                semana=record_data["semana"],
            )
        except RecordValidationError as exc:
            for msg in exc.errors:
                st.error(msg)
        else:
            confirm_overwrite_dialog(int(record_id), record_data)


def _render_bulk_import() -> None:
    st.markdown("##### Importação em Lote via Excel")
    st.caption(
        "Faça upload de uma planilha Excel com novos lançamentos. "
        "Registros duplicados (mesma Oficina + MP + Semana) são ignorados automaticamente."
    )

    _REQUIRED_COLS = [
        "Frete", "MP", "Oficinas", "Data Efetivos", "QTD Efetivos",
        "Data Trabalhados", "QTD Trabalhados", "Contratatação", "Demissão", "Semana",
    ]
    chips_html = "".join(f'<span class="col-chip">{col}</span>' for col in _REQUIRED_COLS)

    st.markdown(
        f"""
        <div class="import-info-box">
            <div class="iib-title">Colunas obrigatórias</div>
            <div class="iib-desc">
                A planilha deve conter exatamente os cabeçalhos abaixo
                (respeite maiúsculas, acentuação e espaços):
            </div>
            <div class="col-chips">{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)",
        type=["xlsx"],
        help="Carregue uma planilha no formato de colunas listado acima."
    )

    if uploaded_file is None:
        return

    with error_boundary("processar o arquivo importado"):
        df_uploaded = pd.read_excel(uploaded_file)

        st.markdown(
            f"""
            <div class="form-section-hdr" style="margin-top:1rem;">
                <span class="fsh-title">Pré-visualização</span>
                <span class="fsh-hint">{len(df_uploaded)} linhas encontradas · exibindo as 10 primeiras</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(df_uploaded.head(10), use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Confirmar Importação em Lote", use_container_width=True, type="primary"):
            with st.spinner("Gravando dados no banco..."):
                linhas_inseridas = insert_bulk_records(df_uploaded)
                st.cache_data.clear()

            if linhas_inseridas > 0:
                st.success(
                    f"Importação concluída! **{linhas_inseridas}** novos registros "
                    f"foram inseridos com sucesso (duplicados ignorados)."
                )
            else:
                st.info(
                    "Nenhum novo registro foi inserido. "
                    "Todos os registros já constavam no banco de dados."
                )
