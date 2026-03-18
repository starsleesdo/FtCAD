from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class PdfExtraction:
    pdf_path: str
    texts: Tuple[str, ...]
    diameters: Tuple[float, ...]
    lengths: Tuple[float, ...]
    pipe_dimensions: Tuple[str, ...]
    title_block: Dict[str, Tuple[str, ...]]


def _dedupe_preserve(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _parse_literal_string(data: bytes, start: int) -> Tuple[bytes, int]:
    # PDF literal string parser for /Contents(...)
    i = start + 1
    depth = 1
    out = bytearray()
    while i < len(data) and depth > 0:
        ch = data[i]
        if ch == 0x5C:  # backslash
            i += 1
            if i >= len(data):
                break
            esc = data[i]
            if esc in b"nrtbf":
                out.append(
                    {
                        ord("n"): 0x0A,
                        ord("r"): 0x0D,
                        ord("t"): 0x09,
                        ord("b"): 0x08,
                        ord("f"): 0x0C,
                    }[esc]
                )
            elif esc in b"\\()":
                out.append(esc)
            elif esc in b"\n\r":
                if esc == 0x0D and i + 1 < len(data) and data[i + 1] == 0x0A:
                    i += 1
            elif 0x30 <= esc <= 0x37:
                oct_digits = [esc]
                for _ in range(2):
                    if i + 1 < len(data) and 0x30 <= data[i + 1] <= 0x37:
                        i += 1
                        oct_digits.append(data[i])
                    else:
                        break
                try:
                    out.append(int(bytes(oct_digits), 8) & 0xFF)
                except Exception:
                    pass
            else:
                out.append(esc)
        elif ch == 0x28:  # '('
            depth += 1
            out.append(ch)
        elif ch == 0x29:  # ')'
            depth -= 1
            if depth > 0:
                out.append(ch)
        else:
            out.append(ch)
        i += 1
    return bytes(out), i


def _extract_pdf_texts(pdf_path: str) -> List[str]:
    data = Path(pdf_path).read_bytes()
    contents: List[bytes] = []
    idx = 0
    needle = b"/Contents"
    while True:
        idx = data.find(needle, idx)
        if idx == -1:
            break
        j = idx + len(needle)
        while j < len(data) and data[j] in b" \t\r\n\f\0":
            j += 1
        if j < len(data) and data[j:j + 1] == b"(":
            raw, end = _parse_literal_string(data, j)
            contents.append(raw)
            idx = end
        else:
            idx = j

    texts: List[str] = []
    for raw in contents:
        if raw.startswith(b"\xfe\xff"):
            try:
                texts.append(raw[2:].decode("utf-16-be", errors="ignore"))
            except Exception:
                continue
        elif raw.startswith(b"\xff\xfe"):
            try:
                texts.append(raw[2:].decode("utf-16-le", errors="ignore"))
            except Exception:
                continue
        else:
            try:
                texts.append(raw.decode("utf-8", errors="ignore"))
            except Exception:
                texts.append(raw.decode("latin-1", errors="ignore"))

    normalized = []
    for text in texts:
        text = text.replace("\r", "\n")
        text = "".join(ch for ch in text if ch >= " " or ch == "\n").strip()
        if text:
            normalized.append(text)
    return _dedupe_preserve(normalized)


def _find_pdf_path(base_dir: str) -> Optional[str]:
    try:
        names = os.listdir(base_dir)
    except OSError:
        return None
    pdfs = [name for name in names if name.lower().endswith(".pdf")]
    if not pdfs:
        return None
    for name in pdfs:
        if "上升管" in name:
            return os.path.join(base_dir, name)
    return os.path.join(base_dir, pdfs[0])


def load_upcomer_pdf_data(base_dir: str) -> Optional[PdfExtraction]:
    pdf_path = _find_pdf_path(base_dir)
    if not pdf_path or not os.path.exists(pdf_path):
        return None
    texts = _extract_pdf_texts(pdf_path)
    if not texts:
        return None

    diameter_re = re.compile(r"[∅Φφ]\s*([0-9]+(?:\.[0-9]+)?)")
    dn_re = re.compile(r"\bDN\s*([0-9]+)\b", re.IGNORECASE)
    scale_re = re.compile(r"\b\d+\s*:\s*\d+\b")
    sheet_re = re.compile(r"\bA[0-9]\b")
    drawing_re = re.compile(r"\bFT/E-[0-9A-Za-z\\-]+\b")

    diameters: List[float] = []
    lengths: List[float] = []
    pipe_dims: List[str] = []
    scales: List[str] = []
    sheets: List[str] = []
    drawings: List[str] = []

    for line in texts:
        if dn_re.search(line) or "NPT" in line or "×" in line or "x" in line and "∅" in line:
            pipe_dims.append(line)
        for match in diameter_re.findall(line):
            try:
                diameters.append(float(match))
            except ValueError:
                pass
        if scale_re.search(line):
            scales.append(scale_re.search(line).group(0).replace(" ", ""))
        if sheet_re.search(line):
            sheets.append(sheet_re.search(line).group(0))
        if drawing_re.search(line):
            drawings.append(drawing_re.search(line).group(0))

        if line.isdigit():
            try:
                value = float(line)
            except ValueError:
                continue
            if 30 <= value <= 10000:
                lengths.append(value)

    diameters = sorted(set(diameters))
    lengths = sorted(set(lengths))
    pipe_dims = _dedupe_preserve(pipe_dims)
    scales = _dedupe_preserve(scales)
    sheets = _dedupe_preserve(sheets)
    drawings = _dedupe_preserve(drawings)

    title_block = {
        "drawing_numbers": tuple(drawings),
        "scales": tuple(scales),
        "sheet_sizes": tuple(sheets),
    }

    return PdfExtraction(
        pdf_path=pdf_path,
        texts=tuple(texts),
        diameters=tuple(diameters),
        lengths=tuple(lengths),
        pipe_dimensions=tuple(pipe_dims),
        title_block=title_block,
    )


def _pick_value(values: Iterable[float], targets: Iterable[float], fallback: float) -> float:
    values_list = list(values)
    for target in targets:
        for value in values_list:
            if abs(value - target) <= 0.5:
                return value
    return fallback


def resolve_inner_cylinder_spec(data: PdfExtraction) -> Dict[str, float]:
    diameters = data.diameters
    lengths = data.lengths

    outer_d = _pick_value(diameters, [560, 550, 520], 560.0)
    inner_d = _pick_value(diameters, [520, 500], max(outer_d - 40.0, 0.0))
    flange_od = _pick_value(diameters, [760, 785], outer_d)
    height = _pick_value(lengths, [2704, 3590, 1350], max(lengths) if lengths else 2000.0)
    flange_thk = _pick_value(lengths, [55, 78, 120], 55.0)

    if inner_d >= outer_d:
        inner_d = max(outer_d - 40.0, 0.0)

    return {
        "outer_diameter": outer_d,
        "inner_diameter": inner_d,
        "flange_outer_diameter": flange_od,
        "height": height,
        "flange_thickness": flange_thk,
    }


def summarize_extraction(data: PdfExtraction) -> str:
    title_items = 0
    for value in data.title_block.values():
        title_items += len(value)
    title_bits = []
    drawing_numbers = data.title_block.get("drawing_numbers", ())
    scales = data.title_block.get("scales", ())
    sheet_sizes = data.title_block.get("sheet_sizes", ())
    if drawing_numbers:
        title_bits.append(f"图号{drawing_numbers[0]}")
    if scales:
        title_bits.append(f"比例{scales[0]}")
    if sheet_sizes:
        title_bits.append(f"图幅{sheet_sizes[0]}")
    title_summary = "、".join(title_bits) if title_bits else f"图框{title_items}项"
    return (
        f"提取到直径{len(data.diameters)}项、长度{len(data.lengths)}项、"
        f"管道{len(data.pipe_dimensions)}项、{title_summary}"
    )
