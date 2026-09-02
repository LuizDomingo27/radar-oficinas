"""Localiza a aba certa dentro de uma planilha, mesmo que ela tenha sido renomeada.

Motivo: as planilhas são reexportadas todo mês e o Excel renomeia abas com
facilidade (a base de postos chegou com "Planilha1" no lugar de "Dados", com o
conteúdo idêntico). Procurar só pelo nome exato fazia o build parar no 1º passo
e o app dizer apenas que "os dados não puderam ser atualizados".

Ordem de resolução (da mais confiável para a mais tolerante):

1. nome exato configurado;
2. nome equivalente (ignorando acento, caixa e espaços extras);
3. **assinatura de cabeçalho** (``config.ABAS_ESPERADAS``) — a única aba cuja
   linha de cabeçalho contém todos os rótulos esperados. É o critério que
   reconhece a aba pelo conteúdo, e por isso sobrevive a qualquer renomeação.

Se nada casar, levanta ``AbaNaoEncontrada`` com as abas disponíveis — falhar é
melhor do que ler a aba errada e publicar números inventados.
"""

from __future__ import annotations

import unicodedata

from app_oficinas import config
from app_oficinas.errors import AbaNaoEncontrada


def _chave(texto: str) -> str:
    """Forma comparável de um rótulo: sem acento, minúsculo, espaços colapsados."""
    decomposto = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def _cabecalho(wb, nome_aba: str, linha: int) -> set[str]:
    """Conjunto de rótulos (normalizados) da linha de cabeçalho de uma aba."""
    ws = wb[nome_aba]
    for valores in ws.iter_rows(min_row=linha, max_row=linha, values_only=True):
        return {_chave(v) for v in valores if v is not None and str(v).strip()}
    return set()


def _por_assinatura(wb, spec: config.AbaEsperada) -> str | None:
    """Nome da única aba cujo cabeçalho contém TODOS os rótulos da assinatura.

    Exige unicidade: se duas abas casarem, o palpite é ambíguo e devolvemos
    ``None`` para cair no erro explícito em vez de escolher no escuro.
    """
    if not spec.assinatura:
        return None
    exigidos = {_chave(r) for r in spec.assinatura}
    casaram = []
    for nome in wb.sheetnames:
        try:
            if exigidos <= _cabecalho(wb, nome, spec.linha_cabecalho):
                casaram.append(nome)
        except Exception:  # aba protegida/ilegível: só não é candidata
            continue
    return casaram[0] if len(casaram) == 1 else None


def resolver(wb, nome_aba: str, arquivo: str) -> str:
    """Nome real da aba dentro de ``wb`` que corresponde a ``nome_aba``.

    Raises:
        AbaNaoEncontrada: nenhuma aba do arquivo corresponde à configurada.
    """
    if nome_aba in wb.sheetnames:
        return nome_aba

    por_chave = {_chave(n): n for n in wb.sheetnames}
    if _chave(nome_aba) in por_chave:
        return por_chave[_chave(nome_aba)]

    achada = _por_assinatura(wb, config.aba_esperada(arquivo, nome_aba))
    if achada:
        return achada

    raise AbaNaoEncontrada(
        f"Aba '{nome_aba}' não existe em {arquivo} e nenhuma outra aba tem o "
        f"cabeçalho esperado. Disponíveis: {wb.sheetnames}"
    )


def abrir_aba(wb, nome_aba: str, arquivo: str):
    """Worksheet correspondente a ``nome_aba`` (resolvendo renomeações)."""
    return wb[resolver(wb, nome_aba, arquivo)]
