"""
core/errors.py — tratamento central de erros da área "Recebimento".

Garante que nenhuma exceção inesperada quebre a interface com um traceback cru:
o usuário recebe uma mensagem amigável e o detalhe técnico fica recolhido.
Espelha ``app_envios/core/errors.py``.
"""

from __future__ import annotations

import functools
import logging
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

import streamlit as st

logger = logging.getLogger("app_recebimento")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] app_recebimento: %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


F = TypeVar("F", bound=Callable)


def _friendly_message(context: str) -> str:
    return (
        f"Ops! Ocorreu um problema ao {context}. "
        "Você pode tentar recarregar a página; se o erro persistir, "
        "acione o suporte com os detalhes técnicos abaixo."
    )


def _render_error(context: str, exc: Exception) -> None:
    logger.exception("Erro ao %s", context)
    st.error(_friendly_message(context))
    with st.expander("Detalhes técnicos (para suporte)"):
        st.code(f"{type(exc).__name__}: {exc}", language="text")


@contextmanager
def error_boundary(context: str, *, fatal: bool = False) -> Iterator[None]:
    """Protege um bloco: captura, registra e converte a exceção em mensagem amigável."""
    try:
        yield
    except Exception as exc:  # noqa: BLE001 — capturar tudo é exatamente o objetivo.
        _render_error(context, exc)
        if fatal:
            st.stop()


def guard(context: str, *, fatal: bool = False) -> Callable[[F], F]:
    """Versão decorator de ``error_boundary``."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with error_boundary(context, fatal=fatal):
                return func(*args, **kwargs)
            return None

        return wrapper  # type: ignore[return-value]

    return decorator
