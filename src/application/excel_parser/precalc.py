"""Utilities for LibreOffice-based Excel cache pre-calculation."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from loguru import logger


class PrecalcMode(str, Enum):
    """Pre-calculation mode resolved from environment."""

    OFF = "off"
    ON = "on"


@dataclass(frozen=True)
class PrecalcSettings:
    """Resolved settings controlling LibreOffice pre-calculation."""

    mode: PrecalcMode
    timeout_sec: int
    outdir: Path | None
    ttl_days: int


def load_precalc_settings() -> PrecalcSettings:
    """Resolve LibreOffice pre-calculation settings from environment."""

    raw_mode = os.getenv("EXCEL_PARSER_PRECALC_MODE", "on").strip().lower()

    if raw_mode in {"0", "false", "disabled", "off"}:
        mode = PrecalcMode.OFF
    else:
        mode = PrecalcMode.ON

    timeout_default = 120
    try:
        timeout_value = int(os.getenv("EXCEL_PARSER_PRECALC_TIMEOUT_SEC", timeout_default))
        if timeout_value <= 0:
            raise ValueError("timeout must be positive")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Invalid EXCEL_PARSER_PRECALC_TIMEOUT_SEC value: %s. Using default=%s.",
            str(exc),
            timeout_default,
        )
        timeout_value = timeout_default

    outdir_raw = os.getenv("EXCEL_PARSER_PRECALC_OUTDIR", "").strip()
    outdir_path = Path(outdir_raw).resolve() if outdir_raw else None

    ttl_default = 7
    try:
        ttl_value = int(os.getenv("EXCEL_PARSER_PRECALC_TTL_DAYS", ttl_default))
        if ttl_value < 0:
            raise ValueError("ttl must be non-negative")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Invalid EXCEL_PARSER_PRECALC_TTL_DAYS value: %s. Using default=%s.",
            str(exc),
            ttl_default,
        )
        ttl_value = ttl_default

    return PrecalcSettings(
        mode=mode,
        timeout_sec=timeout_value,
        outdir=outdir_path,
        ttl_days=ttl_value,
    )


def refresh_excel_cache_if_enabled(excel_path: Path) -> Path:
    """Return a path to recalculated Excel file or original when disabled/fails."""

    settings = load_precalc_settings()

    if settings.mode is PrecalcMode.OFF:
        logger.debug("Excel precalc disabled via EXCEL_PARSER_PRECALC_MODE")
        return excel_path

    try:
        return _ensure_precalculated_copy(excel_path, settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to refresh Excel cache via LibreOffice: %s. Using original file.",
            str(exc),
        )
        return excel_path


def _ensure_precalculated_copy(excel_path: Path, settings: PrecalcSettings) -> Path:
    cache_dir = _resolve_cache_dir(excel_path, settings)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = cache_dir / _build_cache_filename(excel_path)

    if cache_path.exists() and _is_cache_fresh(cache_path, settings.ttl_days):
        logger.debug("Reusing existing precalculated Excel cache: %s", cache_path)
        return cache_path

    _cleanup_stale_cache_files(cache_dir, settings.ttl_days)

    logger.info("Recalculating Excel formulas via LibreOffice headless mode")
    with tempfile.TemporaryDirectory(prefix="excel-precalc-") as tmp_dir:
        tmp_output_dir = Path(tmp_dir)
        _invoke_libreoffice_convert(excel_path, tmp_output_dir, settings.timeout_sec)

        converted_path = _locate_converted_file(tmp_output_dir, excel_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(converted_path), str(cache_path))

    logger.info("Excel precalc completed: %s", cache_path)
    return cache_path


def _invoke_libreoffice_convert(excel_path: Path, output_dir: Path, timeout_sec: int) -> None:
    if shutil.which("libreoffice") is None:
        raise RuntimeError("libreoffice binary not found in PATH")

    command = [
        "libreoffice",
        "--headless",
        "--norestore",
        "--invisible",
        "--convert-to",
        "xlsx",
        "--outdir",
        str(output_dir.resolve()),
        str(excel_path.resolve()),
    ]

    logger.debug("Executing LibreOffice command: %s", " ".join(command))

    try:
        subprocess.run(command, check=True, timeout=timeout_sec, capture_output=True)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("LibreOffice conversion timed out") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else ""
        logger.error("LibreOffice conversion failed: %s", stderr)
        raise RuntimeError("LibreOffice conversion failed") from exc


def _locate_converted_file(output_dir: Path, original_path: Path) -> Path:
    target_name = f"{original_path.stem}.xlsx"
    candidate = output_dir / target_name
    if candidate.exists():
        return candidate

    # Fallback: scan for first xlsx file
    for entry in output_dir.glob("*.xlsx"):
        return entry

    raise FileNotFoundError(
        f"LibreOffice did not produce expected file '{target_name}' in {output_dir}"
    )


def _resolve_cache_dir(excel_path: Path, settings: PrecalcSettings) -> Path:
    if settings.outdir is not None:
        base_dir = settings.outdir
    else:
        base_dir = excel_path.parent

    return base_dir / "excel_precalc_cache"


def _build_cache_filename(excel_path: Path) -> str:
    file_hash = _calculate_md5(excel_path)
    return f"{excel_path.stem}-{file_hash}.xlsx"


def _calculate_md5(file_path: Path) -> str:
    hash_md5 = hashlib.md5()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def _is_cache_fresh(cache_path: Path, ttl_days: int) -> bool:
    if ttl_days == 0:
        return True

    age_seconds = time.time() - cache_path.stat().st_mtime
    return age_seconds <= ttl_days * 86400


def _cleanup_stale_cache_files(cache_dir: Path, ttl_days: int) -> None:
    if ttl_days == 0:
        return

    cutoff = time.time() - ttl_days * 86400

    for file_path in cache_dir.glob("*.xlsx"):
        try:
            if file_path.stat().st_mtime < cutoff:
                logger.debug("Removing stale precalc cache file: %s", file_path)
                file_path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to cleanup cache file %s: %s", file_path, str(exc))


