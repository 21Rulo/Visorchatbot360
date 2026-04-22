import os
from PIL import Image

carpeta_raiz = r'frontend\public\assets'

for carpeta_actual, subcarpetas, archivos in os.walk(carpeta_raiz):
    for nombre_archivo in archivos:
        if nombre_archivo.lower().endswith(('.jpg', '.jpeg', '.png')):
            ruta_origen = os.path.join(carpeta_actual, nombre_archivo)

            nombre_sin_ext = os.path.splitext(nombre_archivo)[0]
            ruta_destino = os.path.join(carpeta_actual, f"{nombre_sin_ext}.webp")

            if os.path.exists(ruta_destino):
                print(f"⏭️ Ya existe: {ruta_destino}")
                continue

            print(f"Procesando: {ruta_origen}...")

            try:
                with Image.open(ruta_origen) as img:
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')

                    img.save(
                        ruta_destino,
                        'WEBP',
                        lossless=True,
                        method=6
                    )

                print(f"✅ Convertido: {ruta_destino}")

            except Exception as e:
                print(f"❌ Error con {nombre_archivo}: {e}")