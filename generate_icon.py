#!/usr/bin/env python3
"""
Script para generar íconos del Verificador DUSA con logo Tu Planilla.
Funciona en Windows y Mac.
"""
import sys
import os
from PIL import Image, ImageDraw

def create_tuplanilla_icon(size=256):
    """Crea el ícono de Tu Planilla programáticamente"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fondo con gradiente simulado (púrpura a rosa)
    for y in range(size):
        r = int(147 + (236 - 147) * y / size)
        g = int(51 + (72 - 51) * y / size)
        b = int(234 + (153 - 234) * y / size)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    
    # Máscara para esquinas redondeadas
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = size // 5
    mask_draw.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=255)
    img.putalpha(mask)
    
    # Dibujar el cubo 3D (logo Tu Planilla) en blanco
    scale = size / 50
    
    # Puntos del cubo (del SVG original)
    points_top = [(25, 10), (38, 18), (25, 26), (12, 18)]
    points_top_scaled = [(int(x * scale), int(y * scale)) for x, y in points_top]
    
    # Líneas del cubo
    lines = [
        ((12, 18), (12, 32)),
        ((25, 26), (25, 40)),
        ((38, 18), (38, 32)),
        ((12, 32), (25, 40)),
        ((25, 40), (38, 32)),
    ]
    
    line_width = max(2, int(2.5 * scale))
    
    # Dibujar polígono superior (sin width para compatibilidad)
    draw.polygon(points_top_scaled, outline='white')
    # Dibujar bordes más gruesos manualmente
    for i in range(len(points_top_scaled)):
        p1 = points_top_scaled[i]
        p2 = points_top_scaled[(i + 1) % len(points_top_scaled)]
        draw.line([p1, p2], fill='white', width=line_width)
    
    # Dibujar líneas del cubo
    for (x1, y1), (x2, y2) in lines:
        draw.line(
            [(int(x1 * scale), int(y1 * scale)), (int(x2 * scale), int(y2 * scale))],
            fill='white',
            width=line_width
        )
    
    return img

def generate_windows_icon(output_path='icon.ico'):
    """Genera un archivo .ico para Windows con múltiples tamaños"""
    sizes = [256, 128, 64, 48, 32, 16]  # De mayor a menor
    icons = [create_tuplanilla_icon(s) for s in sizes]
    
    # Guardar el mayor primero, los demás como append_images
    icons[0].save(
        output_path,
        format='ICO',
        append_images=icons[1:],
    )
    
    # Verificar tamaño del archivo
    import os
    file_size = os.path.getsize(output_path)
    print(f'✅ {output_path} created ({file_size:,} bytes, {len(sizes)} sizes)')

def generate_mac_iconset(output_dir='icon.iconset'):
    """Genera un iconset para Mac"""
    os.makedirs(output_dir, exist_ok=True)
    
    sizes = [16, 32, 64, 128, 256, 512]
    for size in sizes:
        icon = create_tuplanilla_icon(size)
        icon.save(os.path.join(output_dir, f'icon_{size}x{size}.png'), 'PNG')
        if size <= 256:
            icon2x = create_tuplanilla_icon(size * 2)
            icon2x.save(os.path.join(output_dir, f'icon_{size}x{size}@2x.png'), 'PNG')
    
    print(f'✅ {output_dir} created with Tu Planilla logo')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'mac':
        generate_mac_iconset()
    else:
        generate_windows_icon()
