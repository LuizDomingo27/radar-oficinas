"""Testes das partes puras de app_common.scripts.backup_neon (sem tocar no banco)."""
from __future__ import annotations

import json

from app_common.scripts.backup_neon import (
    BackupEntry,
    _host_do_dsn,
    build_manifest,
    safe_filename,
    sha256_of_file,
)


def _entry(tabela: str, linhas: int) -> BackupEntry:
    return BackupEntry(tabela=tabela, arquivo=f"{tabela}.csv", linhas=linhas,
                       bytes=10, sha256="abc")


def test_safe_filename_preserva_case_e_underscore():
    assert safe_filename("Envios_Radar") == "Envios_Radar.csv"
    assert safe_filename("postos") == "postos.csv"


def test_safe_filename_neutraliza_caminho_e_caracteres_invalidos():
    assert "/" not in safe_filename("../etc/passwd")
    assert "\\" not in safe_filename("a\\b")
    assert safe_filename('tab"ela') == "tab_ela.csv"
    assert safe_filename("  ") == "tabela.csv"


def test_sha256_of_file(tmp_path):
    arquivo = tmp_path / "x.csv"
    arquivo.write_bytes(b"abc")
    # SHA-256 conhecido de "abc".
    assert sha256_of_file(arquivo) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_build_manifest_soma_linhas_e_serializa():
    manifesto = build_manifest(
        [_entry("postos", 10), _entry("Envios_Radar", 5)],
        gerado_em="2026-09-15T20:00:00",
        dsn_host="ep-teste.neon.tech",
    )
    assert manifesto["total_tabelas"] == 2
    assert manifesto["total_linhas"] == 15
    assert manifesto["somente_leitura"] is True
    assert manifesto["host"] == "ep-teste.neon.tech"
    assert [t["tabela"] for t in manifesto["tabelas"]] == ["postos", "Envios_Radar"]
    json.dumps(manifesto)  # precisa ser serializável


def test_build_manifest_vazio():
    manifesto = build_manifest([], gerado_em="2026-09-15T20:00:00", dsn_host="h")
    assert manifesto["total_tabelas"] == 0
    assert manifesto["total_linhas"] == 0


def test_host_do_dsn_nao_vaza_credenciais():
    dsn = "postgresql://usuario:senha@ep-teste.neon.tech/neondb?sslmode=require"
    host = _host_do_dsn(dsn)
    assert host == "ep-teste.neon.tech"
    assert "senha" not in host and "usuario" not in host


def test_host_do_dsn_tolera_lixo():
    assert _host_do_dsn("") == ""
