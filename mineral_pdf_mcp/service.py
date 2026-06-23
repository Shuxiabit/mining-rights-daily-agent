from __future__ import annotations

import io
import re

from pypdf import PdfReader

from common.http import fetch_public, offline_mode
from common.models import envelope

DEMO_RESOURCES = [
    {
        "classification": "Indicated",
        "ore_tonnage_mt": 214.0,
        "grade": 1.32,
        "grade_unit": "% Li2O",
        "contained_metal": 2.82,
        "metal_unit": "Mt Li2O",
        "page": 1,
        "evidence": (
            "Demonstration record — Indicated: 214 Mt at 1.32% Li2O, containing 2.82 Mt Li2O."
        ),
    },
    {
        "classification": "Inferred",
        "ore_tonnage_mt": 43.0,
        "grade": 1.21,
        "grade_unit": "% Li2O",
        "contained_metal": 0.52,
        "metal_unit": "Mt Li2O",
        "page": 1,
        "evidence": (
            "Demonstration record — Inferred: 43 Mt at 1.21% Li2O, containing 0.52 Mt Li2O."
        ),
    },
]

ROW_PATTERN = re.compile(
    r"(?P<classification>Indicated|Inferred)"
    r".{0,100}?(?P<tonnage>\d+(?:\.\d+)?)\s*(?:Mt|million\s+tonnes)"
    r".{0,100}?(?P<grade>\d+(?:\.\d+)?)\s*(?P<grade_unit>%\s*(?:Li2O|Cu)|g/t\s*Au)",
    re.IGNORECASE,
)


def calculate_contained_metal(
    tonnage_mt: float, grade: float, grade_unit: str
) -> tuple[float, str]:
    normalized = re.sub(r"\s+", "", grade_unit).lower()
    if normalized in {"%li2o", "%cu"}:
        material = "Li2O" if "li2o" in normalized else "Cu"
        return round(tonnage_mt * grade / 100, 4), f"Mt {material}"
    if normalized == "g/tau":
        ounces = tonnage_mt * 1_000_000 * grade / 31.1034768
        return round(ounces), "oz Au"
    raise ValueError(f"Unsupported grade unit: {grade_unit}")


def extract_resource_rows(pages: list[str]) -> list[dict]:
    rows: list[dict] = []
    for page_number, text in enumerate(pages, start=1):
        normalized = " ".join(text.split())
        for match in ROW_PATTERN.finditer(normalized):
            evidence = match.group(0)
            tonnage = float(match.group("tonnage"))
            grade = float(match.group("grade"))
            grade_unit = re.sub(r"\s+", " ", match.group("grade_unit")).strip()
            contained_metal, metal_unit = calculate_contained_metal(tonnage, grade, grade_unit)
            rows.append(
                {
                    "classification": match.group("classification").title(),
                    "ore_tonnage_mt": tonnage,
                    "grade": grade,
                    "grade_unit": grade_unit,
                    "contained_metal": contained_metal,
                    "metal_unit": metal_unit,
                    "page": page_number,
                    "evidence": evidence,
                }
            )
    return rows


async def extract_resources(pdf_url: str) -> dict:
    if offline_mode() or pdf_url.startswith("demo://"):
        return envelope(
            DEMO_RESOURCES,
            source_url=pdf_url,
            data_status="demo",
            error=(
                "Demonstration resource table; replace demo:// URL with a public report "
                "PDF for live extraction."
            ),
        )
    try:
        content, final_url, _ = await fetch_public(
            pdf_url,
            allowed_content_types=("application/pdf",),
            max_bytes=25_000_000,
        )
        reader = PdfReader(io.BytesIO(content))
        pages = [(page.extract_text() or "") for page in reader.pages]
        rows = extract_resource_rows(pages)
        if not rows:
            return envelope(
                [],
                source_url=pdf_url,
                data_status="unavailable",
                error=(
                    "PDF downloaded, but no supported Indicated/Inferred row pattern was "
                    "found; manual review required."
                ),
            )
        return envelope(rows, source_url=final_url, data_status="live")
    except Exception as exc:
        return envelope(
            [],
            source_url=pdf_url,
            data_status="unavailable",
            error=f"Live PDF extraction unavailable: {exc}",
        )
