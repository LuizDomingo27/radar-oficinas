"""Camada de infraestrutura: leitura das planilhas .xlsx (I/O isolado)."""

from app_oficinas.infra import leitor_fatos
from app_oficinas.infra.leitor_planilha import ler_fonte, ler_todas

__all__ = ["ler_fonte", "ler_todas", "leitor_fatos"]
