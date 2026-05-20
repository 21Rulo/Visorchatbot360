import os
import cv2

# Ruta de tus imágenes (misma que usaste en tu conversor webp)
carpeta_raiz = r'.'

# Cargamos el modelo preentrenado de OpenCV para detección de rostros frontales
# Este archivo XML ya viene instalado por defecto cuando instalas opencv-python
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

print("🕵️ Iniciando escaneo de rostros en la carpeta de assets...")

# Recorremos las carpetas de la misma forma que en tu script webp
for carpeta_actual, subcarpetas, archivos in os.walk(carpeta_raiz):
    for nombre_archivo in archivos:
        # Procesamos JPG, PNG y también WEBP
        if nombre_archivo.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            ruta_imagen = os.path.join(carpeta_actual, nombre_archivo)
            
            # Leer la imagen con OpenCV
            img = cv2.imread(ruta_imagen)
            
            if img is None:
                print(f"⚠️ No se pudo leer la imagen: {ruta_imagen}")
                continue

            # Convertir a escala de grises (necesario para que el modelo detecte los rostros)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Detectar rostros
            # scaleFactor=1.1 y minNeighbors=5 son valores estándar que equilibran precisión y falsos positivos
            rostros = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            # Si se detectaron rostros, los difuminamos
            if len(rostros) > 0:
                print(f"📸 Procesando: {ruta_imagen} - Se encontraron {len(rostros)} rostro(s)")
                
                for (x, y, w, h) in rostros:
                    # Extraer la región de interés (el cuadro donde está el rostro)
                    rostro_roi = img[y:y+h, x:x+w]
                    
                    # Aplicar difuminado gaussiano (el número 99, 99 determina la intensidad del blur. Debe ser impar)
                    rostro_difuminado = cv2.GaussianBlur(rostro_roi, (99, 99), 30)
                    
                    # Reemplazar el rostro original con el difuminado en la imagen
                    img[y:y+h, x:x+w] = rostro_difuminado
                
                # Guardar la imagen sobreescribiendo la original
                cv2.imwrite(ruta_imagen, img)
                print(f"✅ Difuminado aplicado y guardado.")
            else:
                # Opcional: imprimir si quieres ver qué fotos ignoró
                # print(f"⏭️ Sin rostros: {ruta_imagen}")
                pass

print("🎉 Proceso de privacidad finalizado.")