"""
core/errors.py
----------------
Camada central de tratamento de erros da aplicação.

Objetivo: garantir que NENHUMA exceção inesperada quebre a interface com um
traceback cru. Em vez disso, o usuário recebe uma mensagem amigável em
português, e o detalhe técnico fica disponível (recolhido) apenas para suporte.

Uso típico:

    from app_postos.core.errors import error_boundary, guard

    # Como context manager, para proteger um trecho:
    with error_boundary("carregar o dashboard"):
        render_dashboard()

    # Como decorator, para proteger uma função inteira:
    @guard("renderizar os KPIs")
    def render_kpi_section(df): ...

Quando `fatal=True`, a execução da página é interrompida (`st.stop()`) após
exibir a mensagem — útil para falhas das quais não há como seguir (ex.: falha
ao carregar a fonte de dados).
"""

from __future__ import annotations

import functools
import logging
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

import streamlit as st

# Logger dedicado. No Streamlit Cloud a saída vai para os "Manage app logs",
# o que permite investigar o traceback real sem expô-lo ao usuário final.
logger = logging.getLogger("app_postos")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] app_postos: %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


F = TypeVar("F", bound=Callable)


def _friendly_message(context: str) -> str:
    """Monta a mensagem amigável exibida ao usuário para um dado contexto."""
    return (
        f"Ops! Ocorreu um problema ao {context}. "
        "Você pode tentar recarregar a página; se o erro persistir, "
        "acione o suporte com os detalhes técnicos abaixo."
    )


def _render_error(context: str, exc: Exception) -> None:
    """Exibe a mensagem amigável + detalhe técnico recolhido, e registra no log."""
    logger.exception("Erro ao %s", context)
    st.error(_friendly_message(context))
    with st.expander("Detalhes técnicos (para suporte)"):
        st.code(f"{type(exc).__name__}: {exc}", language="text")


@contextmanager
def error_boundary(context: str, *, fatal: bool = False) -> Iterator[None]:
    """
    Protege um bloco de código. Qualquer exceção é capturada, registrada e
    convertida numa mensagem amigável — a aplicação nunca mostra um traceback.

    context: descrição curta em infinitivo do que estava acontecendo,
             ex.: "carregar os dados", "gravar o registro".
    fatal:   se True, chama st.stop() após exibir o erro (interrompe a página).
    """
    try:
        yield
    except Exception as exc:  # noqa: BLE001 — é exatamente o ponto: capturar tudo.
        _render_error(context, exc)
        if fatal:
            st.stop()


def guard(context: str, *, fatal: bool = False) -> Callable[[F], F]:
    """Versão decorator de `error_boundary`, para proteger uma função inteira."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with error_boundary(context, fatal=fatal):
                return func(*args, **kwargs)
            return None

        return wrapper  # type: ignore[return-value]

    return decorator
