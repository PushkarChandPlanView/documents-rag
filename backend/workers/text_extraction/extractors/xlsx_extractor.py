import io
from dataclasses import dataclass

import openpyxl


@dataclass
class ExtractionResult:
    text: str
    page_count: int


def extract(file_bytes: bytes) -> ExtractionResult:
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    parts: list[str] = []
    for sheet in wb.worksheets:
        rows: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                rows.append("\t".join(cells))
        if rows:
            parts.append(f"[Sheet: {sheet.title}]\n" + "\n".join(rows))
    wb.close()
    full_text = "\n\n".join(parts)
    return ExtractionResult(text=full_text, page_count=len(wb.worksheets))
