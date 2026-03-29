#!/usr/bin/env python3
"""
Fetch Excel workbook from SMB share, remove unwanted sheets, convert .xlsm to .xlsx.

Automates the manual workflow:
  1. Download ОперативныйУчет.xlsm from \\\\192.168.1.3\\Share\\Учет
  2. Remove the heavy "Отчеты" sheet (ZIP-level, no openpyxl needed for large files)
  3. Strip VBA macros (.xlsm → .xlsx)
  4. Save as data/real_data_for_testing/Data_source_excel.xlsx

Requires: smbclient CLI (apt install smbclient).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "real_data_for_testing" / "Data_source_excel.xlsx"

# XML namespaces used in Excel Open XML
NS = {
    "ss": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# Content types
XLSM_WORKBOOK_CT = (
    "application/vnd.ms-excel.sheet.macroEnabled.main+xml"
)
XLSX_WORKBOOK_CT = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
)
VBA_CT = "application/vnd.ms-office.vbaProject"


def setup_logging() -> None:
    """Configure console logging for the script."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        colorize=False,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch Excel from SMB share, strip macros and unwanted sheets.",
    )
    parser.add_argument(
        "--host",
        default="192.168.1.3",
        help="SMB server IP (default: 192.168.1.3)",
    )
    parser.add_argument(
        "--share",
        default="Share",
        help="SMB share name (default: Share)",
    )
    parser.add_argument(
        "--remote-path",
        default="Учет",
        help="Directory inside the share (default: Учет)",
    )
    parser.add_argument(
        "--filename",
        default="ОперативныйУчет.xlsm",
        help="Remote filename (default: ОперативныйУчет.xlsm)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output .xlsx path (default: {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)})",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("SMB_USERNAME", ""),
        help="SMB username (default: env SMB_USERNAME or anonymous)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SMB_PASSWORD", ""),
        help="SMB password (default: env SMB_PASSWORD or empty)",
    )
    parser.add_argument(
        "--exclude-sheets",
        nargs="+",
        default=["Отчеты"],
        help="Sheet names to remove (default: Отчеты)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup of existing output file",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip openpyxl verification of the result",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# SMB download
# ---------------------------------------------------------------------------

def check_smbclient() -> bool:
    """Check if smbclient is available in PATH."""
    return shutil.which("smbclient") is not None


def download_from_smb(
    host: str,
    share: str,
    remote_path: str,
    filename: str,
    local_path: Path,
    username: str = "",
    password: str = "",
) -> None:
    """Download a file from SMB share using smbclient CLI."""
    if not check_smbclient():
        logger.error(
            "smbclient not found. Install it: sudo apt install smbclient"
        )
        raise SystemExit(1)

    smb_cmd = f'cd "{remote_path}"; get "{filename}" "{local_path}"'
    cmd = [
        "smbclient",
        f"//{host}/{share}",
    ]

    if username:
        cmd += ["-U", f"{username}%{password}"]
    else:
        cmd += ["-N"]  # anonymous (no password)

    cmd += ["-c", smb_cmd]

    logger.info("Downloading from SMB: //{}/{}/{}/{}", host, share, remote_path, filename)
    logger.debug("Command: {}", " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        logger.error("smbclient failed (exit code {})", result.returncode)
        if result.stderr:
            logger.error("stderr: {}", result.stderr.strip())
        if result.stdout:
            logger.error("stdout: {}", result.stdout.strip())
        raise SystemExit(1)

    if not local_path.exists() or local_path.stat().st_size == 0:
        logger.error("Downloaded file is missing or empty: {}", local_path)
        raise SystemExit(1)

    size_mb = local_path.stat().st_size / (1024 * 1024)
    logger.info("Downloaded {:.1f} MB to {}", size_mb, local_path)


# ---------------------------------------------------------------------------
# ZIP-level .xlsm → .xlsx conversion
# ---------------------------------------------------------------------------

def _register_xml_namespaces() -> None:
    """Register common Excel XML namespaces to preserve prefixes on output."""
    prefixes = {
        "": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
        "x14ac": "http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac",
        "xr": "http://schemas.microsoft.com/office/spreadsheetml/2014/revision",
        "xr6": "http://schemas.microsoft.com/office/spreadsheetml/2014/revision6",
        "xr10": "http://schemas.microsoft.com/office/spreadsheetml/2014/revision10",
        "xr2": "http://schemas.microsoft.com/office/spreadsheetml/2015/revision2",
    }
    for prefix, uri in prefixes.items():
        ET.register_namespace(prefix, uri)


def _find_sheets_info(
    workbook_xml: bytes,
    sheet_names: list[str],
) -> dict[str, dict[str, str | int]]:
    """Find sheet r:id, sheetId, and zero-based index from xl/workbook.xml.

    Returns dict mapping sheet_name -> {"r_id": ..., "sheet_id": ..., "index": ...}.
    """
    root = ET.fromstring(workbook_xml)
    sheets_el = root.find("ss:sheets", NS)
    if sheets_el is None:
        logger.warning("No <sheets> element found in workbook.xml")
        return {}

    result: dict[str, dict[str, str | int]] = {}
    for idx, sheet_el in enumerate(sheets_el.findall("ss:sheet", NS)):
        name = sheet_el.get("name", "")
        if name in sheet_names:
            r_id = sheet_el.get(f"{{{NS['r']}}}id", "")
            sheet_id = sheet_el.get("sheetId", "")
            result[name] = {"r_id": r_id, "sheet_id": sheet_id, "index": idx}
            logger.info(
                "Found sheet '{}': r:id={}, sheetId={}, index={}",
                name, r_id, sheet_id, idx,
            )
    return result


def _resolve_sheet_targets(
    rels_xml: bytes,
    r_ids: set[str],
) -> dict[str, str]:
    """Resolve relationship IDs to target file paths from xl/_rels/workbook.xml.rels.

    Returns dict mapping r_id -> target path (e.g. "worksheets/sheet5.xml").
    """
    root = ET.fromstring(rels_xml)
    result: dict[str, str] = {}
    for rel in root.findall("rel:Relationship", NS):
        rid = rel.get("Id", "")
        if rid in r_ids:
            target = rel.get("Target", "")
            result[rid] = target
            logger.info("Resolved {}: {}", rid, target)
    return result


def _resolve_vba_rel_id(rels_xml: bytes) -> str | None:
    """Find relationship ID for vbaProject.bin if present."""
    root = ET.fromstring(rels_xml)
    for rel in root.findall("rel:Relationship", NS):
        target = rel.get("Target", "")
        if "vbaProject" in target:
            return rel.get("Id", "")
    return None


def _patch_content_types(
    xml_bytes: bytes,
    skip_parts: set[str],
) -> bytes:
    """Remove overrides for deleted sheets and vbaProject; fix workbook content type."""
    _register_xml_namespaces()
    ET.register_namespace("", NS["ct"])

    root = ET.fromstring(xml_bytes)

    to_remove = []
    for override in root.findall(f"{{{NS['ct']}}}Override"):
        part_name = override.get("PartName", "")
        content_type = override.get("ContentType", "")

        # Remove overrides for skipped sheet files
        # part_name looks like "/xl/worksheets/sheet5.xml"
        stripped = part_name.lstrip("/")
        if stripped in skip_parts:
            to_remove.append(override)
            logger.debug("Removing content type override: {}", part_name)
            continue

        # Remove vbaProject override
        if VBA_CT in content_type:
            to_remove.append(override)
            logger.debug("Removing vbaProject content type override")
            continue

        # Switch workbook content type from macro-enabled to regular
        if content_type == XLSM_WORKBOOK_CT:
            override.set("ContentType", XLSX_WORKBOOK_CT)
            logger.debug("Switched workbook content type to xlsx")

    for el in to_remove:
        root.remove(el)

    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def _patch_workbook_xml(
    xml_bytes: bytes,
    sheet_names: set[str],
    removed_indices: set[int],
) -> bytes:
    """Remove <sheet> elements and related <definedName> entries."""
    _register_xml_namespaces()

    root = ET.fromstring(xml_bytes)
    sheets_el = root.find("ss:sheets", NS)

    if sheets_el is not None:
        to_remove = []
        for sheet_el in sheets_el.findall("ss:sheet", NS):
            if sheet_el.get("name", "") in sheet_names:
                to_remove.append(sheet_el)
        for el in to_remove:
            sheets_el.remove(el)
            logger.debug("Removed <sheet> element: {}", el.get("name"))

    # Remove definedNames with localSheetId pointing to removed sheets
    # and adjust localSheetId for sheets after removed ones
    defined_names_el = root.find("ss:definedNames", NS)
    if defined_names_el is not None:
        to_remove = []
        sorted_removed = sorted(removed_indices)

        for dn in defined_names_el.findall("ss:definedName", NS):
            local_id_str = dn.get("localSheetId")
            if local_id_str is None:
                continue
            local_id = int(local_id_str)

            if local_id in removed_indices:
                to_remove.append(dn)
                logger.debug(
                    "Removing definedName '{}' (localSheetId={})",
                    dn.get("name", "?"), local_id,
                )
            else:
                # Adjust index: shift down by number of removed sheets before this one
                shift = sum(1 for ri in sorted_removed if ri < local_id)
                if shift > 0:
                    dn.set("localSheetId", str(local_id - shift))

        for el in to_remove:
            defined_names_el.remove(el)

        # Remove <definedNames> entirely if empty
        if len(defined_names_el) == 0:
            root.remove(defined_names_el)

    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def _patch_workbook_rels(
    xml_bytes: bytes,
    remove_r_ids: set[str],
) -> bytes:
    """Remove <Relationship> elements for deleted sheets and vbaProject."""
    ET.register_namespace("", NS["rel"])

    root = ET.fromstring(xml_bytes)
    to_remove = []
    for rel in root.findall(f"{{{NS['rel']}}}Relationship"):
        rid = rel.get("Id", "")
        target = rel.get("Target", "")
        if rid in remove_r_ids or "vbaProject" in target:
            to_remove.append(rel)
            logger.debug("Removing relationship: {} -> {}", rid, target)

    for el in to_remove:
        root.remove(el)

    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def _patch_calc_chain(
    xml_bytes: bytes,
    removed_sheet_ids: set[str],
) -> bytes | None:
    """Remove <c> elements referencing deleted sheet IDs from calcChain.xml.

    Returns None if the result is empty (file should be skipped).
    """
    _register_xml_namespaces()

    root = ET.fromstring(xml_bytes)
    to_remove = []
    for c_el in root.findall("ss:c", NS):
        if c_el.get("i", "") in removed_sheet_ids:
            to_remove.append(c_el)

    for el in to_remove:
        root.remove(el)

    if len(root) == 0:
        logger.debug("calcChain.xml is empty after patching, will be removed")
        return None

    logger.debug(
        "calcChain.xml: removed {} entries, {} remaining",
        len(to_remove), len(root),
    )
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def convert_xlsm_to_xlsx(
    source: Path,
    target: Path,
    exclude_sheets: list[str],
) -> None:
    """Convert .xlsm to .xlsx by removing VBA and specified sheets at ZIP level."""
    logger.info("Converting {} -> {}", source.name, target.name)
    logger.info("Sheets to remove: {}", exclude_sheets)

    _register_xml_namespaces()

    with zipfile.ZipFile(source, "r") as zin:
        # Step 1: Read workbook.xml and rels to find sheet info
        workbook_xml = zin.read("xl/workbook.xml")
        rels_xml = zin.read("xl/_rels/workbook.xml.rels")

        sheets_info = _find_sheets_info(workbook_xml, exclude_sheets)
        if not sheets_info:
            logger.warning(
                "None of the sheets {} found in workbook. "
                "Proceeding with VBA removal only.",
                exclude_sheets,
            )

        # Collect r:ids and resolve to file paths
        r_ids = {info["r_id"] for info in sheets_info.values()}
        targets_map = _resolve_sheet_targets(rels_xml, r_ids)

        # Also find vbaProject relationship id
        vba_r_id = _resolve_vba_rel_id(rels_xml)
        remove_r_ids = r_ids.copy()
        if vba_r_id:
            remove_r_ids.add(vba_r_id)

        # Build skip set (full paths within ZIP)
        skip_files: set[str] = {"xl/vbaProject.bin"}
        skip_parts_for_ct: set[str] = {"xl/vbaProject.bin"}

        for r_id, rel_target in targets_map.items():
            # rel_target is like "worksheets/sheet5.xml"
            full_path = f"xl/{rel_target}"
            rels_path = f"xl/worksheets/_rels/{Path(rel_target).name}.rels"
            skip_files.add(full_path)
            skip_files.add(rels_path)
            skip_parts_for_ct.add(full_path)
            logger.info("Will skip: {}", full_path)

        removed_indices = {
            int(info["index"]) for info in sheets_info.values()
        }
        removed_sheet_ids = {
            str(info["sheet_id"]) for info in sheets_info.values()
        }

        # Step 2: Create new ZIP, patching metadata on the fly
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in skip_files:
                    logger.debug("Skipping: {}", item.filename)
                    continue

                if item.filename == "[Content_Types].xml":
                    ct_xml = zin.read(item.filename)
                    patched = _patch_content_types(ct_xml, skip_parts_for_ct)
                    zout.writestr(item, patched)

                elif item.filename == "xl/workbook.xml":
                    patched = _patch_workbook_xml(
                        workbook_xml,
                        set(sheets_info.keys()),
                        removed_indices,
                    )
                    zout.writestr(item, patched)

                elif item.filename == "xl/_rels/workbook.xml.rels":
                    patched = _patch_workbook_rels(rels_xml, remove_r_ids)
                    zout.writestr(item, patched)

                elif item.filename == "xl/calcChain.xml":
                    calc_xml = zin.read(item.filename)
                    patched_calc = _patch_calc_chain(
                        calc_xml, removed_sheet_ids,
                    )
                    if patched_calc is not None:
                        zout.writestr(item, patched_calc)
                    else:
                        logger.debug("Skipping empty calcChain.xml")

                else:
                    # Copy entry as-is (streaming via read)
                    data = zin.read(item.filename)
                    zout.writestr(item, data)

    source_mb = source.stat().st_size / (1024 * 1024)
    target_mb = target.stat().st_size / (1024 * 1024)
    logger.info(
        "Conversion done: {:.1f} MB -> {:.1f} MB ({:.0f}% reduction)",
        source_mb, target_mb, (1 - target_mb / source_mb) * 100,
    )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_xlsx(xlsx_path: Path, excluded_sheets: list[str]) -> bool:
    """Verify the resulting .xlsx opens with openpyxl and has no excluded sheets."""
    try:
        from openpyxl import load_workbook

        wb = load_workbook(xlsx_path, read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        wb.close()

        if not sheet_names:
            logger.error("Verification FAILED: workbook has no sheets")
            return False

        for excluded in excluded_sheets:
            if excluded in sheet_names:
                logger.error(
                    "Verification FAILED: sheet '{}' still present", excluded,
                )
                return False

        logger.info(
            "Verification OK: {} sheets, excluded sheets absent. Sheets: {}",
            len(sheet_names),
            ", ".join(sheet_names[:5]) + ("..." if len(sheet_names) > 5 else ""),
        )
        return True

    except Exception as exc:
        logger.error("Verification FAILED: {}", exc)
        return False


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

MAX_BACKUPS = 15


def _cleanup_old_backups(backup_dir: Path, suffix: str = ".xlsx") -> None:
    """Remove oldest backups if count exceeds MAX_BACKUPS."""
    backups = sorted(
        backup_dir.glob(f"*{suffix}"), key=lambda p: p.stat().st_mtime,
    )
    while len(backups) > MAX_BACKUPS:
        oldest = backups.pop(0)
        oldest.unlink()
        logger.info("Removed old backup: {}", oldest.name)


def create_backup(file_path: Path) -> Path | None:
    """Create a backup copy in a dedicated backup directory.

    Backup is saved as <backup_dir>/<stem>_<YYYYMMDD_HHMMSS>.xlsx.
    If more than MAX_BACKUPS files exist, the oldest is removed.
    """
    if not file_path.exists():
        return None

    backup_dir = file_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
    backup_path = backup_dir / backup_name

    shutil.copy2(file_path, backup_path)

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    logger.info("Backup created: {} ({:.1f} MB)", backup_path.name, size_mb)

    _cleanup_old_backups(backup_dir, suffix=file_path.suffix)
    return backup_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load .env from project root if available."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        logger.debug("Loaded .env from {}", env_path)


def main() -> int:
    """Entry point: download, convert, verify."""
    setup_logging()
    _load_dotenv()
    args = parse_args()

    output: Path = args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    # Download .xlsm to temp file
    with tempfile.TemporaryDirectory(prefix="fetch_excel_") as tmpdir:
        tmp_xlsm = Path(tmpdir) / args.filename
        download_from_smb(
            host=args.host,
            share=args.share,
            remote_path=args.remote_path,
            filename=args.filename,
            local_path=tmp_xlsm,
            username=args.username,
            password=args.password,
        )

        # Convert .xlsm -> .xlsx (temp location)
        tmp_xlsx = Path(tmpdir) / "result.xlsx"
        convert_xlsm_to_xlsx(tmp_xlsm, tmp_xlsx, args.exclude_sheets)

        # Verify before replacing
        if not args.skip_verify:
            if not verify_xlsx(tmp_xlsx, args.exclude_sheets):
                logger.error("Verification failed, aborting. Original file unchanged.")
                return 1

        # Backup existing file
        if not args.no_backup:
            create_backup(output)

        # Atomic replace
        shutil.copy2(tmp_xlsx, output)
        logger.info("Saved: {}", output)

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
