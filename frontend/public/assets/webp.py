import os
from PIL import Image

# Ruta principal
carpeta_raiz = r'frontend\public\assets'

for carpeta_actual, subcarpetas, archivos in os.walk(carpeta_raiz):
    for nombre_archivo in archivos:
        if nombre_archivo.lower().endswith(('.jpg', '.jpeg', '.png')):
            ruta_origen = os.path.join(carpeta_actual, nombre_archivo)

            nombre_sin_ext = os.path.splitext(nombre_archivo)[0]
            ruta_destino = os.path.join(carpeta_actual, f"{nombre_sin_ext}.webp")

            # Si ya existe el webp, lo saltamos
            if os.path.exists(ruta_destino):
                print(f"⏭️ Ya existe: {ruta_destino}")
                continue

            print(f"Procesando: {ruta_origen}...")

            try:
                with Image.open(ruta_origen) as img:
                    # Redimensionar si es más grande que 4096 px
                    if img.width > 4096:
                        proporcion = 4096 / img.width
                        nuevo_alto = int(img.height * proporcion)
                        img = img.resize((4096, nuevo_alto), Image.Resampling.LANCZOS)

                    # Convertir a RGB si viene en PNG con transparencia o modos raros
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')

                    # Guardar en la misma carpeta
                    img.save(ruta_destino, 'WEBP', quality=80, method=6)

                print(f"✅ Convertido: {ruta_destino}")

                # BORRAR ORIGINAL (opcional)
                os.remove(ruta_origen)
                print(f"🗑️ Eliminado original: {ruta_origen}")

            except Exception as e:
                print(f"❌ Error con {nombre_archivo}: {e}")