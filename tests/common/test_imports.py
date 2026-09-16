"""
Teste de fumaça: todo módulo do app precisa ser importável.

Por que existe: a suíte cobre `core/` e `services/`, mas nada importava as
camadas `ui/`/`dashboard`. Um import quebrado (nome removido, reexport que
alguém ainda usava) só aparecia ao abrir a tela — tarde demais. Este teste
varre os pacotes e importa cada módulo, transformando esse tipo de erro em
falha de suíte.

Não exercita comportamento; apenas garante que nada ficou pendurado.
"""
from __future__ import annotations

import importlib
import pkgutil

import pytest

PACOTES = ["app_common", "app_oficinas", "app_postos", "app_envios", "app_recebimento"]


def _modulos() -> list[str]:
    """Todos os módulos importáveis dos pacotes do app, em ordem estável."""
    encontrados: list[str] = []
    for nome_pacote in PACOTES:
        pacote = importlib.import_module(nome_pacote)
        encontrados.append(nome_pacote)
        for info in pkgutil.walk_packages(pacote.__path__, prefix=f"{nome_pacote}."):
            # `scripts` são pontos de entrada de linha de comando: importá-los
            # é seguro, mas eles puxam planilha/banco em tempo de execução, não
            # de import — por isso entram na varredura como os demais.
            encontrados.append(info.name)
    return sorted(set(encontrados))


@pytest.mark.parametrize("modulo", _modulos())
def test_modulo_importa(modulo: str) -> None:
    importlib.import_module(modulo)
