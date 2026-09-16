"""
ui/cadastro_view.py — importação em lote de envios (planilha → Neon).

Os envios vêm da planilha ENVIOS_OFICINAS.xlsx, re-exportada periodicamente.
A regra anti-duplicação (row_hash) garante que só os envios NOVOS entrem —
re-subir a mesma planilha não insere nada e nada é apagado/sobrescrito.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_envios.core.config import RawColumns
from app_envios.core.errors import error_boundary
from app_envios.services.data_writer import insert_bulk_records

_REQUIRED_COLS = [
    RawColumns.ORIGEM, RawColumns.ORDEM, RawColumns.OFICINA, RawColumns.QTD,
    RawColumns.MINUTOS, RawColumns.ENVIO, RawColumns.MP, RawColumns.PDV,
    RawColumns.FRETE, RawColumns.SITUACAO,
]


def render_cadastro_page() -> None:
    """Página de importação em lote da planilha de envios."""
    st.markdown(
        """
        <div class="app-header">
            <div class="title-row"><h1>Lançamento de Dados — Envios</h1></div>
            <div class="subtitle">Importe a planilha de envios; apenas os registros novos são gravados</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### Importação em Lote via Excel")
    st.caption(
        "Faça upload da planilha de envios (.xlsx). Envios que já constam no "
        "banco (mesma impressão digital de linha) são ignorados automaticamente."
    )

    chips_html = "".join(f'<span class="col-chip">{col}</span>' for col in _REQUIRED_COLS)
    st.markdown(
        f"""
        <div class="import-info-box">
            <div class="iib-title">Colunas obrigatórias</div>
            <div class="iib-desc">
                A planilha deve conter os cabeçalhos abaixo (a ordem não importa):
            </div>
            <div class="col-chips">{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])
    if uploaded_file is None:
        return

    with error_boundary("processar o arquivo importado"):
        df_uploaded = pd.read_excel(uploaded_file)
        df_uploaded.columns = [str(c).strip() for c in df_uploaded.columns]

        faltando = [c for c in _REQUIRED_COLS if c not in df_uploaded.columns]
        if faltando:
            st.error(
                "A planilha está sem as colunas obrigatórias: "
                + ", ".join(faltando)
                + f". Colunas encontradas: {list(df_uploaded.columns)}"
            )
            return

        st.markdown(
            f"""
            <div class="form-section-hdr" style="margin-top:1rem;">
                <span class="fsh-title">Pré-visualização</span>
                <span class="fsh-hint">{len(df_uploaded)} linhas · exibindo as 10 primeiras</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(df_uploaded.head(10), use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Confirmar Importação em Lote", use_container_width=True, type="primary"):
            with st.spinner("Gravando envios no banco..."):
                inseridos = insert_bulk_records(df_uploaded)
                st.cache_data.clear()

            if inseridos > 0:
                st.success(
                    f"Importação concluída! **{inseridos}** novo(s) envio(s) "
                    "inserido(s) (duplicados ignorados)."
                )
            else:
                st.info(
                    "Nenhum envio novo foi inserido — todos os registros já "
                    "constavam no banco de dados."
                )
