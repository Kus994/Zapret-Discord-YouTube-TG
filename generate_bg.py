"""Generate a dark gradient background with subtle geometric patterns and glow effects."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math
import random

W, H = 1920, 1080

img = Image.new("RGB", (W, H), (6, 8, 14))
draw = ImageDraw.Draw(img)

# --- Layer 1: Deep gradient base ---
for y in range(H):
    r = int(6 + (y / H) * 4)
    g = int(8 + (y / H) * 3)
    b = int(14 + (y / H) * 8)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# --- Layer 2: Subtle radial glow spots ---
glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow_layer)

# Amber glow top-right
cx, cy = int(W * 0.72), int(H * 0.22)
for r in range(300, 0, -1):
    alpha = int(18 * (1 - r / 300))
    glow_draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(245, 166, 35, alpha)
    )

# Dim blue glow bottom-left
cx, cy = int(W * 0.25), int(H * 0.78)
for r in range(250, 0, -1):
    alpha = int(12 * (1 - r / 250))
    glow_draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(30, 80, 180, alpha)
    )

# Small accent glow center
cx, cy = int(W * 0.5), int(H * 0.45)
for r in range(150, 0, -1):
    alpha = int(8 * (1 - r / 150))
    glow_draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(245, 166, 35, alpha)
    )

img.paste(Image.alpha_composite(
    img.convert("RGBA"), glow_layer
).convert("RGB"))

# --- Layer 3: Subtle grid pattern ---
grid_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
grid_draw = ImageDraw.Draw(grid_layer)

spacing = 60
for x in range(0, W, spacing):
    grid_draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 5), width=1)
for y in range(0, H, spacing):
    grid_draw.line([(0, y), (W, y)], fill=(255, 255, 255, 5), width=1)

img.paste(Image.alpha_composite(
    img.convert("RGBA"), grid_layer
).convert("RGB"))

# --- Layer 4: Diagonal accent lines ---
line_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
line_draw = ImageDraw.Draw(line_layer)

random.seed(42)
for _ in range(8):
    x1 = random.randint(-200, W + 200)
    y1 = random.randint(-200, H + 200)
    length = random.randint(200, 500)
    angle = random.uniform(-0.3, 0.3)
    x2 = x1 + int(length * math.cos(angle))
    y2 = y1 + int(length * math.sin(angle))
    line_draw.line(
        [(x1, y1), (x2, y2)],
        fill=(245, 166, 35, 12),
        width=1
    )

img.paste(Image.alpha_composite(
    img.convert("RGBA"), line_layer
).convert("RGB"))

# --- Layer 5: Subtle noise texture ---
noise_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
noise_draw = ImageDraw.Draw(noise_layer)

random.seed(123)
for _ in range(8000):
    x = random.randint(0, W - 1)
    y = random.randint(0, H - 1)
    alpha = random.randint(2, 8)
    noise_draw.point((x, y), fill=(255, 255, 255, alpha))

img.paste(Image.alpha_composite(
    img.convert("RGBA"), noise_layer
).convert("RGB"))

# --- Layer 6: Soft vignette ---
vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
vig_draw = ImageDraw.Draw(vignette)

cx, cy = W // 2, H // 2
max_r = int(math.sqrt(cx**2 + cy**2))
for r in range(max_r, 0, -2):
    progress = r / max_r
    alpha = int(60 * progress**2)
    alpha = min(alpha, 120)
    vig_draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(0, 0, 0, alpha)
    )

img.paste(Image.alpha_composite(
    img.convert("RGBA"), vignette
).convert("RGB"))

# --- Final: slight blur for smoothness ---
img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

# Save
from pathlib import Path
out = str(Path(__file__).parent / "assets" / "background.png")
img.save(out, "PNG", quality=95)
print(f"Background saved: {out} ({img.size[0]}x{img.size[1]})")
