"""Crta ikone za stranicu s akcijama (postotak na narančastom kvadratu).

Pokretanje:  python scripts/ikone.py site/akcije
Rezultat:    icon-192.png, icon-512.png, apple-touch-icon.png

Ikone se ne mijenjaju svaki dan - skripta se pokreće ručno, rezultat ide u git.
Samo standardna biblioteka, bez ovisnosti.
"""

import struct
import sys
import zlib
from pathlib import Path

BG = (194, 65, 12)       # narančasta, ista boja kao oznaka akcije na stranici
FG = (255, 255, 255)
SS = 4                   # uzorkovanje 4x4 po pikselu, da rubovi ne budu nazubljeni


def write_png(path: Path, size: int, rows):
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    head = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head)
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def in_rounded_square(x, y, r):
    """Zaobljeni kvadrat stranice 1 s radijusom r."""
    dx = max(r - x, x - (1 - r), 0)
    dy = max(r - y, y - (1 - r), 0)
    return dx * dx + dy * dy <= r * r


def in_percent(x, y):
    """Znak postotka: dva prstena i kosa crta."""
    for cx, cy in ((0.32, 0.32), (0.68, 0.68)):
        d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        if 0.075 <= d <= 0.15:
            return True
    # kosa crta: udaljenost od pravca x + y = 1, unutar dijagonalnog raspona
    if abs(x + y - 1) <= 0.053 * 2 ** 0.5 and 0.2 <= x <= 0.8:
        return True
    return False


def icon(size: int, maskable: bool = False):
    """maskable: pun kvadrat i manji znak, jer Android ikonu reže na svoj oblik."""
    radius, scale = (0, 0.72) if maskable else (0.22, 1.0)
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            hits = bg_hits = 0
            for sy in range(SS):
                for sx in range(SS):
                    x = (px + (sx + 0.5) / SS) / size
                    y = (py + (sy + 0.5) / SS) / size
                    if in_rounded_square(x, y, radius):
                        bg_hits += 1
                        if in_percent(0.5 + (x - 0.5) / scale, 0.5 + (y - 0.5) / scale):
                            hits += 1
            n = SS * SS
            alpha = round(255 * bg_hits / n)
            k = hits / bg_hits if bg_hits else 0
            row.append(tuple(round(b + (f - b) * k) for b, f in zip(BG, FG)) + (alpha,))
        rows.append(row)
    return rows


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "site/akcije")
    out.mkdir(parents=True, exist_ok=True)
    for name, size, maskable in (("icon-192.png", 192, False), ("icon-512.png", 512, False),
                                 ("icon-maskable-512.png", 512, True), ("apple-touch-icon.png", 180, True)):
        write_png(out / name, size, icon(size, maskable))
        print(f"{out / name} ({size}x{size}){' maskable' if maskable else ''}")


if __name__ == "__main__":
    main()
