"""Componente de interface para exportar a base ou o recorte do dashboard."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from app_postos.core.errors import error_boundary
from app_postos.services.export_service import DataExportError, build_excel_export
from app_postos.services.monthly_report_service import (
    build_monthly_excel_report,
    build_monthly_pdf_report,
    build_monthly_summary,
)
from app_postos.services.weekly_report_service import (
    build_weekly_excel_report,
    build_weekly_pdf_report,
    build_weekly_summary,
)

_FILTERED_SCOPE = "Filtros atuais"
_FULL_SCOPE = "Todos os dados"


@st.cache_data(show_spinner="Preparando o arquivo Excel...")
def _get_export_file(df: pd.DataFrame, scope_description: str) -> bytes:
    """Mantém o arquivo em cache enquanto os dados e o escopo não mudarem."""
    return build_excel_export(df, scope_description)


@st.cache_data(show_spinner="Preparando o resumo semanal em Excel...")
def _get_weekly_excel_file(df: pd.DataFrame, scope_description: str) -> bytes:
    return build_weekly_excel_report(df, scope_description)


@st.cache_data(show_spinner="Preparando o resumo semanal em PDF...")
def _get_weekly_pdf_file(df: pd.DataFrame, scope_description: str) -> bytes:
    return build_weekly_pdf_report(df, scope_description)


@st.cache_data(show_spinner="Preparando o resumo mensal em Excel...")
def _get_monthly_excel_file(df: pd.DataFrame, scope_description: str) -> bytes:
    return build_monthly_excel_report(df, scope_description)


@st.cache_data(show_spinner="Preparando o resumo mensal em PDF...")
def _get_monthly_pdf_file(df: pd.DataFrame, scope_description: str) -> bytes:
    return build_monthly_pdf_report(df, scope_description)


def render_export_controls(df_filtered: pd.DataFrame, df_full: pd.DataFrame) -> None:
    """
    Exibe o resumo semanal filtrado em Excel/PDF e o Excel detalhado.

    O resumo sempre usa ``df_filtered``. Somente a exportação detalhada permite
    alternar entre o recorte atual e a base completa.
    """
    st.markdown("#### Exportar dados")
    try:
        weekly_summary = build_weekly_summary(df_filtered)
        report_year = int(weekly_summary["ano"].iloc[0])
        weekly_description = (
            f"{_build_scope_description(_FILTERED_SCOPE)} Ano: {report_year}."
        )
        weekly_excel_file = _get_weekly_excel_file(df_filtered, weekly_description)
        weekly_pdf_file = _get_weekly_pdf_file(df_filtered, weekly_description)
        monthly_summary = build_monthly_summary(df_filtered)
        monthly_excel_file = _get_monthly_excel_file(df_filtered, weekly_description)
        monthly_pdf_file = _get_monthly_pdf_file(df_filtered, weekly_description)
    except DataExportError as exc:
        st.warning(f"Não foi possível preparar a exportação: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - garante uma interface estável caso o cache falhe.
        with error_boundary("preparar os arquivos de exportação"):
            raise exc
        return

    st.markdown("##### Resumo agrupado por semana")
    st.caption(
        "Totais de efetivos, trabalhados, ausências e absenteísmo, "
        "consolidados por semana. O arquivo sempre respeita ano, mês, MP, "
        "oficinas e semanas selecionados nos filtros acima."
    )
    weekly_stem = _build_weekly_filename_stem(report_year)
    monthly_stem = _build_monthly_filename_stem(report_year)

    st.caption("No arquivo detalhado, escolha o escopo antes de baixar:")
    scope = st.radio(
        "Conteúdo do arquivo detalhado",
        options=(_FILTERED_SCOPE, _FULL_SCOPE),
        horizontal=True,
        help="Escolha entre os registros visíveis pelos filtros ou toda a base carregada.",
        key="export_scope",
        label_visibility="collapsed",
    )
    is_filtered = scope == _FILTERED_SCOPE
    export_df = df_filtered if is_filtered else df_full
    description = _build_scope_description(scope)
    filename = _build_filename(is_filtered)
    try:
        excel_file = _get_export_file(export_df, description)
    except DataExportError as exc:
        st.warning(f"Não foi possível preparar a exportação detalhada: {exc}")
        excel_file = None
    except Exception as exc:  # noqa: BLE001 - mantém a interface estável.
        with error_boundary("preparar a exportação detalhada em Excel"):
            raise exc
        excel_file = None

    # Um container horizontal dimensiona cada item pelo próprio conteúdo.
    # Diferente de st.columns, não distribui os botões por toda a largura.
    with st.container(
        horizontal=True,
        horizontal_alignment="left",
        vertical_alignment="center",
        gap="small",
    ):
        st.download_button(
            "Semanal · Excel",
            data=weekly_excel_file,
            file_name=f"{weekly_stem}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=False,
            key="download_weekly_excel",
        )
        st.download_button(
            "Semanal · PDF",
            data=weekly_pdf_file,
            file_name=f"{weekly_stem}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=False,
            key="download_weekly_pdf",
        )
        st.download_button(
            "Mensal · Excel",
            data=monthly_excel_file,
            file_name=f"{monthly_stem}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=False,
            key="download_monthly_excel",
        )
        st.download_button(
            "Mensal · PDF",
            data=monthly_pdf_file,
            file_name=f"{monthly_stem}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=False,
            key="download_monthly_pdf",
        )
        if excel_file is not None:
            st.download_button(
                "Exportar Tudo",
                data=excel_file,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=False,
                key="download_excel",
            )

    st.caption(
        f"{len(weekly_summary):,} semanas e {len(monthly_summary):,} meses serão "
        "exportados com os filtros selecionados."
        .replace(",", ".")
    )
    st.caption(
        f"O arquivo detalhado contém {len(export_df):,} registros ({scope.lower()})."
        .replace(",", ".")
    )


def _build_scope_description(scope: str) -> str:
    if scope == _FULL_SCOPE:
        return "Base completa, sem considerar os filtros do dashboard."
    return "Recorte conforme os filtros ativos no dashboard."


def _build_filename(is_filtered: bool) -> str:
    scope = "filtros" if is_filtered else "base_completa"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"postos_{scope}_{timestamp}.xlsx"


def _build_weekly_filename_stem(year: int) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"postos_resumo_semanal_{year}_filtros_{timestamp}"


def _build_monthly_filename_stem(year: int) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"postos_resumo_mensal_{year}_filtros_{timestamp}"
