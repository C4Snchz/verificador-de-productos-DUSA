#!/usr/bin/env python3
"""Genera íconos PNG para la extensión de Chrome"""
import struct
import zlib

def create_png(width, height, r, g, b):
    """Crea un PNG simple de color sólido"""
    def png_chunk(chunk_type, data):
        chunk_len = struct.pack('>I', len(data))
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc
    
    signature = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter byte
        for x in range(width):
            raw_data += bytes([r, g, b])
    
    compressed = zlib.compress(raw_data)
    
    return signature + png_chunk(b'IHDR', ihdr) + png_chunk(b'IDAT', compressed) + png_chunk(b'IEND', b'')

import os

# Color azul DUSA: #1e3c72 = rgb(30, 60, 114)
r, g, b = 30, 60, 114

# Directorio del script
script_dir = os.path.dirname(os.path.abspath(__file__))
icons_dir = os.path.join(script_dir, 'icons')

icons = [
    (16, 'icon16.png'),
    (48, 'icon48.png'),
    (128, 'icon128.png')
]

for size, name in icons:
    filepath = os.path.join(icons_dir, name)
    with open(filepath, 'wb') as f:
        f.write(create_png(size, size, r, g, b))
    print(f'Creado: {name}')

print('¡Íconos creados!')
