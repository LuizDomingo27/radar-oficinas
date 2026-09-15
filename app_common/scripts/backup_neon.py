"""
app_common/scripts/backup_neon.py — cópia de segurança (somente leitura) do Neon.

Motivo: antes de qualquer migração, deploy ou carga em lote, queremos uma rede de
proteção fora do banco. Este script NÃO escreve nada no Neon — ele apenas lê as
tabelas do app e grava um CSV por tabela em ``backups/neon_<timestamp>/``, mais um
``manifest.json`` com a contagem de linhas e o SHA-256 de cada arquivo (para
provar, depois, que o backup não foi corrompido).

Uso:
    py -3.12 -m app_common.scripts.backup_neon
    py -3.12 -m app_common.scripts.backup_neon postos Envios_Radar

Sem argumentos, salva as três tabelas do app. Os arquivos ficam fora do Git
(``backups/`` está no .gitignore) — são dados de produção, não código.

Restauração: o CSV tem cabeçalho e é aceito pelo ``COPY ... FROM``. Restaurar é
uma operação MANUAL e deliberada; este script não a automatiza de propósito, para
que nenhuma execução acidental sobrescreva dados bons.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from app_common.neon_client import _qi, _read_dsn  # noqa: E402

# Tabelas mantidas pelo app (as demais do schema não são nossas).
DEFAULT_TABLES = ["postos", "Envios_Radar", "Recebimento_Radar"]

BACKUP_ROOT = BASE_DIR / "backups"
_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class BackupEntry:
    """Resultado do dump de uma tabela."""

    tabela: str
    arquivo: str
    linhas: int
    bytes: int
    sha256: str


def safe_filename(table: str) -> str:
    """
    Nome de arquivo seguro para uma tabela (``Envios_Radar`` → ``Envios_Radar.csv``).

    Preserva letras, dígitos, ``_``, ``-`` e ``.``; qualquer outro caractere vira
    ``_``. Protege contra nomes de tabela com caminho embutido (``../``) ou com
    caracteres inválidos no Windows.
    """
    limpo = "".join(c if (c.isalnum() or c in "_-.") else "_" for c in str(table).strip())
    limpo = limpo.strip(".") or "tabela"
    return f"{limpo}.csv"


def sha256_of_file(path: Path) -> str:
    """SHA-256 do arquivo, lido em blocos (não carrega tudo na memória)."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for bloco in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(bloco)
    return digest.hexdigest()


def build_manifest(entries: list[BackupEntry], *, gerado_em: str, dsn_host: str) -> dict:
    """Manifesto do backup: quando, de onde e o que foi salvo (com checksums)."""
    return {
        "gerado_em": gerado_em,
        "host": dsn_host,
        "somente_leitura": True,
        "total_tabelas": len(entries),
        "total_linhas": sum(e.linhas for e in entries),
        "tabelas": [asdict(e) for e in entries],
    }


def _host_do_dsn(dsn: str) -> str:
    """Host do DSN, SEM usuário/senha — o manifesto nunca guarda credenciais."""
    try:
        depois_do_arroba = dsn.rsplit("@", 1)[-1]
        return depois_do_arroba.split("/", 1)[0].split("?", 1)[0]
    except Exception:  # noqa: BLE001 — manifesto não pode quebrar por isso
        return "desconhecido"


def dump_table(conn, tabela: str, destino: Path) -> BackupEntry:
    """Grava ``tabela`` como CSV em ``destino`` usando ``COPY ... TO STDOUT`` (só leitura)."""
    linhas = 0
    with conn.cursor() as cur:
        cur.execute(f"select count(*) from public.{_qi(tabela)}")
        linhas = int(cur.fetchone()[0])
        with destino.open("wb") as fh:
            with cur.copy(
                f"copy (select * from public.{_qi(tabela)} order by 1) "
                "to stdout with (format csv, header true)"
            ) as copy:
                for bloco in copy:
                    fh.write(bloco)
    return BackupEntry(
        tabela=tabela,
        arquivo=destino.name,
        linhas=linhas,
        bytes=destino.stat().st_size,
        sha256=sha256_of_file(destino),
    )


def main(argv: list[str] | None = None) -> int:
    tabelas = list(argv) if argv else list(DEFAULT_TABLES)
    try:
        import psycopg
    except Exception as exc:  # noqa: BLE001
        print(f"FALHOU: driver psycopg indisponível ({type(exc).__name__}: {exc}).")
        print("Rode com o interpretador do projeto: py -3.12 -m app_common.scripts.backup_neon")
        return 1

    try:
        dsn = _read_dsn(direct=True)
    except Exception as exc:  # noqa: BLE001
        print(f"FALHOU: não foi possível ler a conexão do Neon — {type(exc).__name__}: {exc}")
        return 1

    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta = BACKUP_ROOT / f"neon_{carimbo}"
    pasta.mkdir(parents=True, exist_ok=True)
    print(f"Backup (somente leitura) em {pasta}")

    entries: list[BackupEntry] = []
    try:
        with psycopg.connect(dsn, connect_timeout=30) as conn:
            for tabela in tabelas:
                destino = pasta / safe_filename(tabela)
                try:
                    entry = dump_table(conn, tabela, destino)
                except Exception as exc:  # noqa: BLE001 — uma tabela ruim não aborta o resto
                    conn.rollback()
                    print(f"   [FALHA] {tabela}: {type(exc).__name__}: {exc}")
                    continue
                entries.append(entry)
                print(f"   [OK] {tabela}: {entry.linhas} linha(s), {entry.bytes} bytes")
    except Exception as exc:  # noqa: BLE001
        print(f"FALHOU ao conectar no Neon: {type(exc).__name__}: {exc}")
        return 1

    manifesto = build_manifest(
        entries,
        gerado_em=datetime.now().isoformat(timespec="seconds"),
        dsn_host=_host_do_dsn(dsn),
    )
    (pasta / "manifest.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if len(entries) != len(tabelas):
        print(f"\nConcluído COM FALHAS: {len(entries)}/{len(tabelas)} tabela(s) salvas.")
        return 1
    print(f"\nConcluído. {manifesto['total_linhas']} linha(s) salvas em {len(entries)} tabela(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
