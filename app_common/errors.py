"""
app_common/errors.py — fábrica do tratamento central de erros das áreas.

Objetivo: garantir que NENHUMA exceção inesperada quebre a interface com um
traceback cru. O usuário recebe uma mensagem amigável em português e o detalhe
técnico fica recolhido, disponível apenas para suporte.

Cada área chama ``build_error_handlers`` uma vez, no seu ``core/errors.py``, e
ganha o par ``(error_boundary, guard)`` já amarrado ao seu próprio logger — o
que preserva a separação dos logs por área sem duplicar a mecânica:

    # app_envios/core/errors.py
    error_boundary, guard = build_error_handlers("app_envios")

EXCEÇÃO DE CAMADA DECLARADA: este módulo importa ``streamlit`` de propósito —
é ele quem converte exceção em mensagem de tela.
"""

from __future__ import annotations

import functools
import logging
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

import streamlit as st

F = TypeVar("F", bound=Callable)


def _build_logger(area: str) -> logging.Logger:
    """
    Logger dedicado da área. No Streamlit Cloud a saída vai para os "Manage app
    logs", o que permite investigar o traceback real sem expô-lo ao usuário.
    """
    logger = logging.getLogger(area)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(f"%(asctime)s [%(levelname)s] {area}: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def friendly_message(context: str) -> str:
    """Mensagem amigável exibida ao usuário para um dado contexto."""
    return (
        f"Ops! Ocorreu um problema ao {context}. "
        "Você pode tentar recarregar a página; se o erro persistir, "
        "acione o suporte com os detalhes técnicos abaixo."
    )


def build_error_handlers(area: str) -> tuple[Callable, Callable]:
    """
    Devolve ``(error_boundary, guard)`` para a área informada.

    error_boundary: context manager que protege um bloco.
    guard:          decorator que protege uma função inteira.

    Em ambos, ``context`` é uma descrição curta em infinitivo do que estava
    acontecendo ("carregar os dados", "gravar o registro") e ``fatal=True``
    interrompe a página (``st.stop()``) depois de exibir o erro — útil para
    falhas das quais não há como seguir.
    """
    logger = _build_logger(area)

    def _render_error(context: str, exc: Exception) -> None:
        logger.exception("Erro ao %s", context)
        st.error(friendly_message(context))
        with st.expander("Detalhes técnicos (para suporte)"):
            st.code(f"{type(exc).__name__}: {exc}", language="text")

    @contextmanager
    def error_boundary(context: str, *, fatal: bool = False) -> Iterator[None]:
        try:
            yield
        except Exception as exc:  # noqa: BLE001 — é exatamente o ponto: capturar tudo.
            _render_error(context, exc)
            if fatal:
                st.stop()

    def guard(context: str, *, fatal: bool = False) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with error_boundary(context, fatal=fatal):
                    return func(*args, **kwargs)
                return None

            return wrapper  # type: ignore[return-value]

        return decorator

    return error_boundary, guard
