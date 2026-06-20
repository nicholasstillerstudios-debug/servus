"""Gera assets/jarvis.ico com gradient orbe."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).parent.parent / "assets" / "servus.ico"
OUT.parent.mkdir(parents=True, exist_ok=True)

SIZE = 512
img = Image.new("RGBA", (SIZE, SIZE), (10, 14, 26, 0))
d = ImageDraw.Draw(img)

# bg arredondado (transparente nas pontas, escuro no centro)
d.rounded_rectangle((20, 20, SIZE-20, SIZE-20), radius=90, fill=(10, 14, 26, 255))

# halo externo
halo = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
hd = ImageDraw.Draw(halo)
for i, alpha in enumerate([30, 50, 80]):
    r = 230 - i * 30
    hd.ellipse((SIZE//2 - r, SIZE//2 - r, SIZE//2 + r, SIZE//2 + r),
               outline=(76, 201, 255, alpha), width=3)
halo = halo.filter(ImageFilter.GaussianBlur(6))
img.alpha_composite(halo)

# orbe (gradient radial: branco -> azul -> roxo)
orb_size = 260
orb = Image.new("RGBA", (orb_size, orb_size), (0, 0, 0, 0))
od = ImageDraw.Draw(orb)
for r in range(orb_size // 2, 0, -1):
    t = r / (orb_size / 2)
    # mistura: centro branco-azul, borda roxa
    rr = int(76  * t + 200 * (1 - t))
    gg = int(92  * t + 230 * (1 - t))
    bb = int(255 * t + 255 * (1 - t))
    # tinge pra roxo nas bordas
    rr = int(rr * (1 - t * 0.3) + 122 * t * 0.6)
    gg = int(gg * (1 - t * 0.6) + 92  * t * 0.4)
    bb = int(bb)
    od.ellipse(
        (orb_size//2 - r, orb_size//2 - r, orb_size//2 + r, orb_size//2 + r),
        fill=(rr, gg, bb, 255),
    )

# highlight superior esquerdo
hl = Image.new("RGBA", (orb_size, orb_size), (0, 0, 0, 0))
hld = ImageDraw.Draw(hl)
hld.ellipse((40, 30, 150, 110), fill=(255, 255, 255, 110))
hl = hl.filter(ImageFilter.GaussianBlur(14))
orb.alpha_composite(hl)

img.alpha_composite(orb, ((SIZE - orb_size) // 2, (SIZE - orb_size) // 2))

# salva multi-resolução .ico
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save(OUT, format="ICO", sizes=sizes)
print(f"ok -> {OUT}")
