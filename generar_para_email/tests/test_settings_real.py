import logging
from pathlib import Path

from src import settings


def test_cargar_env_carga_variables(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
# comentario
LOG_LEVEL=DEBUG
FACTURAS_DIR=facturas_test
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("FACTURAS_DIR", raising=False)

    settings._cargar_env(env_file)

    assert "LOG_LEVEL" in __import__("os").environ
    assert __import__("os").environ["LOG_LEVEL"] == "DEBUG"


def test_ruta_desde_env_relativa(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "_BASE", tmp_path)
    monkeypatch.setenv("FACTURAS_DIR", "facturas_rel")

    ruta = settings._ruta_desde_env("FACTURAS_DIR", "facturas")

    assert ruta == (tmp_path / "facturas_rel").resolve()


def test_ruta_desde_env_defecto(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "_BASE", tmp_path)
    monkeypatch.delenv("LOG_FILE", raising=False)

    ruta = settings._ruta_desde_env("LOG_FILE", "logs/app.log")

    assert ruta == (tmp_path / "logs" / "app.log").resolve()


def test_configurar_logging_crea_rotating_handler(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "_BASE", tmp_path)
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "logs" / "app.log"))
    monkeypatch.setenv("LOG_MAX_BYTES", "12345")
    monkeypatch.setenv("LOG_BACKUP_COUNT", "3")

    logger_root = settings._configurar_logging()

    handlers = logger_root.handlers
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)
    rotating = [h for h in handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
    assert len(rotating) == 1
    assert rotating[0].maxBytes == 12345
    assert rotating[0].backupCount == 3


def test_configurar_logging_valores_invalidos(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "_BASE", tmp_path)
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "logs" / "app.log"))
    monkeypatch.setenv("LOG_MAX_BYTES", "no-num")
    monkeypatch.setenv("LOG_BACKUP_COUNT", "no-num")

    logger_root = settings._configurar_logging()
    rotating = [h for h in logger_root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]

    assert len(rotating) == 1
    assert rotating[0].maxBytes == 5242880
    assert rotating[0].backupCount == 5
