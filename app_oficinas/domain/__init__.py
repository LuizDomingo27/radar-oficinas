"""Modelos de domínio — estruturas puras, sem I/O nem dependências externas."""

from app_oficinas.domain.models import Oficina, RegistroNome, VarianteNome

__all__ = ["RegistroNome", "VarianteNome", "Oficina"]
