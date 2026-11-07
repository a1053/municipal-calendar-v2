"""Genera los íconos de la app (site/icons). Se corre a mano; los PNG ya están en el repo.

Es una "M" sobre el vino del sitio, no el escudo del club (la marca es de sus dueños).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = next((ROOT / "scripts" / "fonts").glob("*Bold*.ttf"), None) or next((ROOT / "scripts" / "fonts").glob("*.ttf"))
VINO, ROJO = (43, 10, 15), (208, 28, 36)


def icon(size: int, maskable: bool) -> Image.Image:
    img = Image.new("RGBA", (size, size), VINO)
    d = ImageDraw.Draw(img)
    # Zona segura: los íconos "maskable" se recortan, así que el dibujo ocupa el 60% central.
    box = int(size * (0.6 if maskable else 0.76))
    off = (size - box) // 2
    if not maskable:
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=VINO)
    d.ellipse([off, off, off + box, off + box], fill=ROJO)
    font = ImageFont.truetype(str(FONT), int(box * 0.62))
    d.text((size / 2, size / 2 + box * 0.02), "M", font=font, fill=(255, 255, 255), anchor="mm")
    return img


if __name__ == "__main__":
    out = ROOT / "site" / "icons"
    out.mkdir(exist_ok=True)
    for name, size, mask in [("icon-192.png", 192, False), ("icon-512.png", 512, False),
                             ("maskable-512.png", 512, True), ("apple-touch-icon.png", 180, False)]:
        icon(size, mask).convert("RGB" if mask or "apple" in name else "RGBA").save(out / name)
    print("íconos listos en", out)
