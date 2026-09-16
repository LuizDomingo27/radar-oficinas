"""
core/errors.py — tratamento central de erros da área "Gestão de Postos".

A mecânica (mensagem amigável na tela, detalhe técnico recolhido, log no
servidor) vive em ``app_common.errors``; aqui só a amarramos ao logger desta
área, para que os logs continuem separados por módulo no Streamlit Cloud.

Uso típico:

    from app_postos.core.errors import error_boundary, guard

    with error_boundary("carregar o dashboard"):
        render_dashboard()

    @guard("renderizar os KPIs")
    def render_kpi_section(df): ...
"""

from __future__ import annotations

from app_common.errors import build_error_handlers

error_boundary, guard = build_error_handlers("app_postos")
