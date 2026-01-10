"""
Genera un diagrama esperado de test-auto-layout.gag usando PIL/Pillow.
Representa la estructura esperada según el archivo .gag.
"""

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Crear canvas 800x600
width, height = 800, 600
img = Image.new('RGB', (width, height), 'white')
draw = ImageDraw.Draw(img)

# Fuente por defecto
try:
    font = ImageFont.truetype("arial.ttf", 11)
    font_badge = ImageFont.truetype("arial.ttf", 11)
except:
    font = ImageFont.load_default()
    font_badge = ImageFont.load_default()

# Definir posiciones esperadas (auto-layout en niveles jerárquicos)
# Nivel 0: Frontend
# Nivel 1: REST API
# Nivel 2: Database, Redis Cache

# Frontend (lightgreen server) - Nivel 0, arriba
frontend_x, frontend_y = 400, 100
frontend_w, frontend_h = 80, 60

# REST API (lightblue server) - Nivel 1, medio
api_x, api_y = 400, 250
api_w, api_h = 80, 60

# Database (orange building) - Nivel 2, abajo izquierda
db_x, db_y = 300, 450
db_w, db_h = 80, 60

# Redis Cache (cyan cloud) - Nivel 2, abajo derecha
cache_x, cache_y = 500, 450
cache_w, cache_h = 80, 60

# Dibujar conexiones primero (debajo de los elementos)
# Frontend -> API (HTTP)
draw.line([
    (frontend_x + frontend_w//2, frontend_y + frontend_h),
    (api_x + api_w//2, api_y)
], fill='black', width=2)
draw.text((400, 175), "HTTP", fill='black', font=font)

# API -> Database (SQL)
draw.line([
    (api_x + api_w//2, api_y + api_h),
    (db_x + db_w//2, db_y)
], fill='black', width=2)
draw.text((350, 350), "SQL", fill='black', font=font)

# API -> Cache (GET/SET)
draw.line([
    (api_x + api_w//2, api_y + api_h),
    (cache_x + cache_w//2, cache_y)
], fill='black', width=2)
draw.text((450, 350), "GET/SET", fill='black', font=font)

# Dibujar elementos (encima de las líneas)

# Frontend (lightgreen server - rectángulo con pequeño indicador)
draw.rectangle([frontend_x, frontend_y, frontend_x + frontend_w, frontend_y + frontend_h],
               fill='lightgreen', outline='black', width=2)
draw.rectangle([frontend_x + 5, frontend_y + 5, frontend_x + frontend_w - 5, frontend_y + 15],
               fill='darkgreen', outline='darkgreen')
draw.text((frontend_x + 10, frontend_y + 35), "Frontend", fill='black', font=font)

# REST API (lightblue server)
draw.rectangle([api_x, api_y, api_x + api_w, api_y + api_h],
               fill='lightblue', outline='black', width=2)
draw.rectangle([api_x + 5, api_y + 5, api_x + api_w - 5, api_y + 15],
               fill='darkblue', outline='darkblue')
draw.text((api_x + 8, api_y + 35), "REST API", fill='black', font=font)

# Database (orange building - rectángulo con techo triangular)
draw.rectangle([db_x, db_y + 15, db_x + db_w, db_y + db_h],
               fill='orange', outline='black', width=2)
draw.polygon([
    (db_x, db_y + 15),
    (db_x + db_w//2, db_y),
    (db_x + db_w, db_y + 15)
], fill='darkorange', outline='black')
draw.text((db_x + 8, db_y + 40), "Database", fill='black', font=font)

# Redis Cache (cyan cloud - óvalos superpuestos)
draw.ellipse([cache_x + 10, cache_y, cache_x + 30, cache_y + 25],
             fill='cyan', outline='black', width=2)
draw.ellipse([cache_x + 25, cache_y + 5, cache_x + 55, cache_y + 30],
             fill='cyan', outline='black', width=2)
draw.ellipse([cache_x + 50, cache_y, cache_x + 70, cache_y + 25],
             fill='cyan', outline='black', width=2)
draw.ellipse([cache_x + 5, cache_y + 15, cache_x + 75, cache_y + 45],
             fill='cyan', outline='black', width=2)
draw.text((cache_x + 3, cache_y + 50), "Redis Cache", fill='black', font=font)

# Badge de debug (esquina superior derecha)
badge_x = width - 200
badge_y = 10
badge_w = 190
badge_h = 60

# Rectángulo de fondo semi-transparente
badge_bg = Image.new('RGBA', (badge_w, badge_h), (255, 255, 255, 217))
badge_draw = ImageDraw.Draw(badge_bg)
badge_draw.rectangle([0, 0, badge_w, badge_h], outline='#CCCCCC', width=1)

# Textos del badge
fecha_texto = f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
version_texto = "GAG v2.0.0"

badge_draw.text((10, 12), fecha_texto, fill='red', font=font_badge)
badge_draw.text((10, 32), version_texto, fill='red', font=font_badge)

# Convertir a RGB y pegar
badge_rgb = Image.new('RGB', img.size, 'white')
badge_rgb.paste(img)
badge_rgb.paste(badge_bg, (badge_x, badge_y), badge_bg)

# Guardar
badge_rgb.save('debugs/test-auto-layout-expected-AI.png')
print("[OK] PNG esperado generado: debugs/test-auto-layout-expected-AI.png")
