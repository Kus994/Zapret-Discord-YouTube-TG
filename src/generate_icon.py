"""Generate app icon: amber gradient square with K letter, multiple sizes for .ico."""
from PIL import Image, ImageDraw, ImageFont
import os

sizes = [16, 24, 32, 48, 64, 128, 256]
images = []

for sz in sizes:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background
    pad = max(1, sz // 16)
    r = max(2, sz // 6)
    draw.rounded_rectangle(
        [pad, pad, sz - pad - 1, sz - pad - 1],
        radius=r,
        fill=(245, 166, 35, 255)
    )

    # Darker bottom half for gradient feel
    for y in range(sz // 2, sz - pad):
        alpha = int(80 * (y - sz // 2) / (sz // 2))
        draw.line([(pad, y), (sz - pad - 1, y)], fill=(0, 0, 0, alpha))

    # Letter K
    font_size = int(sz * 0.55)
    try:
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "K", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (sz - tw) // 2
    ty = (sz - th) // 2 - bbox[1]
    draw.text((tx, ty), "K", fill=(10, 12, 18, 255), font=font)

    images.append(img)

# Save as .ico with multiple sizes
from pathlib import Path
_assets = Path(__file__).parent / "assets"
ico_path = str(_assets / "icon.ico")
images[0].save(
    ico_path,
    format="ICO",
    sizes=[(s, s) for s in sizes],
    append_images=images[1:]
)
print(f"Icon saved: {ico_path}")

# Also save 256x256 PNG for preview
png_path = str(_assets / "icon.png")
images[-1].save(png_path, "PNG")
print(f"PNG icon saved: {png_path}")
