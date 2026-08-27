"""Radar de Oficinas — núcleo da aplicação de eficiência de parceiros.

Camadas:
- ``domain``   : modelos puros, sem I/O.
- ``infra``    : leitura das planilhas (openpyxl).
- ``services`` : regras de negócio (normalização, De-Para/matching).

A Fase 1 entrega a dimensão canônica de oficinas (De-Para).
"""

__all__ = ["config", "errors"]
__version__ = "0.1.0"
