"""Генерация синей аватарки для KUS Pro v1.0.0"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

SIZE = 1024
img = Image.new("RGBA", (SIZE, SIZE), (10, 14, 20, 255))
draw = ImageDraw.Draw(img)

# 1. Тёмный фон с градиентом
for y in range(SIZE):
    for x in range(SIZE):
        dist = math.sqrt((x - SIZE//2)**2 + (y - SIZE//2)**2) / SIZE
        r = int(10 + 5 * dist)
        g = int(14 + 8 * dist)
        b = int(20 + 15 * dist)
        img.putpixel((x, y), (r, g, b, 255))

# 2. Круглое свечение в центре (синий)
center_x, center_y = SIZE // 2, SIZE // 2
for r in range(350, 0, -2):
    alpha = int(40 * (1 - r / 350))
    color = (59, 130, 246, alpha)  # Синий #3b82f6
    draw.ellipse([center_x - r, center_y - r, center_x + r, center_y + r], fill=color)

# 3. Рамка-щит
shield_r = 280
for i in range(6):
    r = shield_r + i
    alpha = max(0, 200 - i * 40)
    draw.ellipse([center_x - r, center_y - r, center_x + r, center_y + r], 
                 outline=(59, 130, 246, alpha), width=3)

# 4. Буква K
try:
    font = ImageFont.truetype("arialbd.ttf", 320)
except:
    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 320)
    except:
        font = ImageFont.load_default()

# Тень буквы
for offset in range(8, 0, -1):
    alpha = int(30 * (1 - offset / 8))
    shadow_color = (0, 0, 0, alpha)
    bbox = font.getbbox("K")
    k_width = bbox[2] - bbox[0]
    k_height = bbox[3] - bbox[1]
    x = center_x - k_width // 2 + offset
    y = center_y - k_height // 2 + offset
    draw.text((x, y), "K", fill=shadow_color, font=font)

# Основная буква K (синяя)
for offset_y in range(-2, 3):
    for offset_x in range(-2, 3):
        alpha = max(0, 255 - abs(offset_y) * 30 - abs(offset_x) * 30)
        color = (59, 130, 246, alpha)  # Синий #3b82f6
        bbox = font.getbbox("K")
        k_width = bbox[2] - bbox[0]
        k_height = bbox[3] - bbox[1]
        x = center_x - k_width // 2 + offset_x
        y = center_y - k_height // 2 + offset_y
        draw.text((x, y), "K", fill=color, font=font)

# 5. Точки-индикаторы вокруг
for angle in range(0, 360, 30):
    rad = math.radians(angle)
    px = int(center_x + 320 * math.cos(rad))
    py = int(center_y + 320 * math.sin(rad))
    draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(59, 130, 246, 180))

# 6. Виньетка
for y in range(SIZE):
    for x in range(SIZE):
        dist = math.sqrt((x - SIZE//2)**2 + (y - SIZE//2)**2) / SIZE
        if dist > 0.6:
            pixel = img.getpixel((x, y))
            factor = max(0, 1 - (dist - 0.6) * 2.5)
            new_pixel = tuple(int(c * factor) for c in pixel[:3]) + (pixel[3],)
            img.putpixel((x, y), new_pixel)

# 7. Мягкое размытие
img = img.filter(ImageFilter.GaussianBlur(radius=1.5))

# Сохраняем PNG
output = r"C:\Users\Кусь\Desktop\KusXXX\assets\icon.png"
img.save(output, "PNG")
print("PNG: " + output)

# Конвертируем в ICO
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
ico_images = []
for s in sizes:
    resized = img.resize(s, Image.Resampling.LANCZOS)
    ico_images.append(resized)

ico_path = r"C:\Users\Кусь\Desktop\KusXXX\assets\icon.ico"
ico_images[0].save(ico_path, format="ICO", sizes=[(s[0], s[1]) for s in sizes], 
                   append_images=ico_images[1:])
print("ICO: " + ico_path)
