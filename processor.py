"""Vector PDF stroke-width adjustment without rasterizing page content."""
from __future__ import annotations
import re
import fitz

MM_TO_PT = 72 / 25.4
NUMBER = rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
WIDTH_RE = re.compile(rb'(?<!\S)(' + NUMBER + rb')(\s+)w(?=\s|$)')


def _mask_non_code(data: bytes) -> bytes:
    """Blank comments, strings, and hex strings while preserving byte offsets."""
    mask = bytearray(data)
    i, n = 0, len(data)
    while i < n:
        c = data[i]
        if c == 37:  # % comment
            j = data.find(b'\n', i)
            if j < 0: j = n
            mask[i:j] = b' ' * (j-i)
            i = j
        elif c == 40:  # (...) string, nested with escaped chars
            start, depth = i, 1
            i += 1
            while i < n and depth:
                if data[i] == 92: i += 2; continue
                if data[i] == 40: depth += 1
                elif data[i] == 41: depth -= 1
                i += 1
            mask[start:i] = b' ' * (i-start)
        elif c == 60 and i + 1 < n and data[i+1] != 60:  # <hex>
            j = data.find(b'>', i+1)
            if j < 0: j = n-1
            mask[i:j+1] = b' ' * (j+1-i)
            i = j+1
        else:
            i += 1
    return bytes(mask)


def _rewrite(data: bytes, target_pt: float, mode: str) -> tuple[bytes, int]:
    visible = _mask_non_code(data)
    matches = list(WIDTH_RE.finditer(visible))
    chunks, last = [], 0
    for m in matches:
        chunks.append(data[last:m.start(1)])
        old = float(m.group(1))
        new = target_pt if mode == 'fixed' else max(0, old) * target_pt
        chunks.append(f'{new:.6f}'.encode('ascii'))
        last = m.end(1)
    chunks.append(data[last:])
    # The initial width applies when a stream has strokes without an explicit w.
    # For multiplier mode, leave the implicit PDF default (1 pt) unchanged.
    result = b''.join(chunks)
    if mode == 'fixed':
        result = f'{target_pt:.6f} w\n'.encode('ascii') + result
    return result, len(matches)


def convert_pdf(source: bytes, thickness_mm: float = 0.3, mode: str = 'fixed', factor: float = 2.0) -> tuple[bytes, dict]:
    if not 0.05 <= thickness_mm <= 2.0:
        raise ValueError('Толщина должна быть от 0,05 до 2,0 мм.')
    if mode not in ('fixed', 'multiply'):
        raise ValueError('Неизвестный режим обработки.')
    if not 1 <= factor <= 20:
        raise ValueError('Коэффициент должен быть от 1 до 20.')
    doc = fitz.open(stream=source, filetype='pdf')
    if doc.needs_pass:
        raise ValueError('PDF защищён паролем.')
    # Process page streams and referenced Form XObjects; never modify image streams.
    xrefs = set()
    for page in doc:
        xrefs.update(page.get_contents())
        for item in page.get_xobjects():
            if item:
                xrefs.add(item[0])
    changed = 0
    for xref in xrefs:
        data = doc.xref_stream(xref)
        if re.search(rb'(?<!\S)BI(?=\s)', _mask_non_code(data)):
            raise ValueError('PDF содержит inline-изображения. Безопасная обработка пока не поддерживается.')
        replacement, count = _rewrite(data, thickness_mm * MM_TO_PT if mode == 'fixed' else factor, mode)
        doc.update_stream(xref, replacement, compress=True)
        changed += count
    output = doc.tobytes(garbage=3, deflate=True)
    stats = {'pages': len(doc), 'operators_changed': changed, 'page_sizes': [(round(p.rect.width, 3), round(p.rect.height, 3)) for p in doc]}
    doc.close()
    return output, stats
