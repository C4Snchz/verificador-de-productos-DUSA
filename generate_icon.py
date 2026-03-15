#!/usr/bin/env python3
"""
Script para generar iconos del Verificador DUSA con logo Tu Planilla.
Funciona en Windows y Mac.
"""
import sys
import os

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Instalando Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw


def create_icon(size=256):
    """Crea el icono de Tu Planilla"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fondo gradiente purpura a rosa
    for y in range(size):
        r = int(147 + (236 - 147) * y / size)
        g = int(51 + (72 - 51) * y / size)
        b = int(234 + (153 - 234) * y / size)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    
    # Esquinas redondeadas
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = size // 5
    mask_draw.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=255)
    img.putalpha(mask)
    
    # Dibujar cubo 3D (logo Tu Planilla)
    scale = size / 50.0
    points = [(25, 10), (38, 18), (25, 26), (12, 18)]
    points_scaled = [(int(x * scale), int(y * scale)) for x, y in points]
    
    lines = [
        ((12, 18), (12, 32)),
        ((25, 26), (25, 40)),
        ((38, 18), (38, 32)),
        ((12, 32), (25, 40)),
        ((25, 40), (38, 32)),
    ]
    
    lw = max(2, int(2.5 * scale))
    
    # Bordes superiores del cubo
    for i in range(len(points_scaled)):
        p1 = points_scaled[i]
        p2 = points_scaled[(i + 1) % len(points_scaled)]
        draw.line([p1, p2], fill='white', width=lw)
    
    # Lineas verticales del cubo
    for (x1, y1), (x2, y2) in lines:
        draw.line(
            [(int(x1 * scale), int(y1 * scale)), (int(x2 * scale), int(y2 * scale))],
            fill='white', width=lw
        )
    
    return img


def generate_ico(output='icon.ico'):
    """Genera archivo .ico para Windows"""
    sizes = [256, 128, 64, 48, 32, 16]
    icons = [create_icon(s) for s in sizes]
    icons[0].save(output, format='ICO', append_images=icons[1:])
    file_size = os.path.getsize(output)
    print(f'OK: {output} ({file_size:,} bytes, {len(sizes)} sizes)')


def generate_iconset(output_dir='icon.iconset'):
    """Genera iconset para Mac"""
    os.makedirs(output_dir, exist_ok=True)
    sizes = [16, 32, 64, 128, 256, 512]
    for size in sizes:
        icon = create_icon(size)
        icon.save(os.path.join(output_dir, f'icon_{size}x{size}.png'), 'PNG')
        if size <= 256:
            icon2x = create_icon(size * 2)
            icon2x.save(os.path.join(output_dir, f'icon_{size}x{size}@2x.png'), 'PNG')
    print(f'OK: {output_dir} created')


if __name__ == '__main__':
    print(f"Python: {sys.version}")
    try:
        print(f"Pillow: {Image.__version__}")
    except Exception:
        pass
    
    if len(sys.argv) > 1 and sys.argv[1] == 'mac':
        generate_iconset()
    else:
        generate_ico()
