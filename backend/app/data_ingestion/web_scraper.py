import os
import sys
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import json

# Importamos la base de datos vectorial de nuestra arquitectura
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.core.vector_db import vector_db

# Headers para evitar ser bloqueados
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
}

class WebIngestor:
    def __init__(self):
        print("🌐 Inicializando Web Ingestor...")

    def extraer_contenido_desde_url(self, url_completa):
        """Extrae HTML a Diccionario (¡Ahora con soporte para Tablas del legacy!)"""
        try:
            response = requests.get(url_completa, headers=headers, verify=False, timeout=10)
            response.raise_for_status()
        except Exception as e:
            return {"url": url_completa, "contenido": None, "error": f"No se pudo acceder: {e}"}

        soup = BeautifulSoup(response.text, 'html.parser')
        contenido = {}
        seccion_actual = "General"
        
        # AGREGAMOS 'table' A LA LISTA DE BÚSQUEDA
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table']):
            if tag.name in ['h1', 'h2', 'h3', 'h4']:
                seccion_actual = tag.get_text(strip=True)
                contenido.setdefault(seccion_actual, [])
            elif tag.name == 'p':
                texto = tag.get_text(strip=True)
                if texto:
                    contenido.setdefault(seccion_actual, []).append(texto)
            elif tag.name in ['ul', 'ol']:
                lista = [li.get_text(strip=True) for li in tag.find_all('li') if li.get_text(strip=True)]
                if lista:
                    contenido.setdefault(seccion_actual, []).append({"lista": lista})
            # LÓGICA RESCATADA DEL LEGACY PARA EXTRAER TABLAS
            elif tag.name == 'table':
                tabla = []
                for fila in tag.find_all('tr'):
                    columnas = [celda.get_text(strip=True) for celda in fila.find_all(['td', 'th'])]
                    if columnas:
                        tabla.append(columnas)
                if tabla:
                    contenido.setdefault(seccion_actual, []).append({"tabla": tabla})

        return {
            "url": url_completa, 
            "contenido": contenido if contenido else None,
            "error": None
        }

    def formatear_a_texto(self, contenido_dict, url):
        """Convierte el diccionario en texto estructurado para el LLM y ChromaDB"""
        if not contenido_dict: return ""
        
        texto_final = f"Fuente Web: {url}\n\n"
        for seccion, elementos in contenido_dict.items():
            texto_final += f"## {seccion}\n"
            for item in elementos:
                if isinstance(item, str):
                    texto_final += f"{item}\n"
                elif isinstance(item, dict) and "lista" in item:
                    for li in item["lista"]:
                        texto_final += f"- {li}\n"
                # FORMATEO DE TABLAS PARA QUE EL LLM LAS ENTIENDA
                elif isinstance(item, dict) and "tabla" in item:
                    texto_final += "Tabla de datos:\n"
                    for fila in item["tabla"]:
                        texto_final += " | ".join(fila) + "\n"
            texto_final += "\n"
        return texto_final

    def ingest_to_chroma(self, text, url, institucion):
        """Sube el texto scrapeado a la base de datos vectorial"""
        if not text.strip(): return
        
        chunks = text.split("## ")
        texts = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip() or chunk.startswith("Fuente Web"): continue
            
            clean_text = f"Información extraída de: {url}\nSección: {chunk.strip()}"
            texts.append(clean_text)
            metadatas.append({
                "source": url, 
                "type": "web_scraping",
                "institucion": institucion.upper()
            })
            ids.append(f"web_{hash(url)}_chunk_{i}")
            
        if texts:
            vector_db.add_documents(texts, metadatas, ids)
            print(f"📦 URL {url} indexada en ChromaDB ({len(texts)} fragmentos)")

    
    def scrapear_e_ingestar(self, url, institucion="GENERAL"):
        """Ejecuta el flujo completo para una URL"""
        print(f"Buscando en: {url}")
        resultado = self.extraer_contenido_desde_url(url)
        
        if resultado.get("error"):
            print(f"❌ Error: {resultado.get('error')}")
            return

        if resultado.get("contenido"):
            texto_formateado = self.formatear_a_texto(resultado["contenido"], url)
            self.ingest_to_chroma(texto_formateado, url, institucion)
            print("✅ Web scrapeada e ingestada con éxito.")
        else:
            print("⚠️ No se encontró contenido útil en la página.")

    def procesar_desde_archivo(self, filename="urls_scraping.json"):
        """Lee el archivo JSON y scrappea todas las URLs configuradas"""
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                
            print(f"📄 Archivo de URLs cargado. Comenzando scraping masivo...\n")
            
            for institucion, urls in datos.items():
                print(f"🏫 === Procesando institución: {institucion} ===")
                for url in urls:
                    self.scrapear_e_ingestar(url, institucion)
                    
            print("\n✅ Scraping masivo finalizado.")
            
        except FileNotFoundError:
            print(f"❌ Error: No se encontró el archivo {filename}")
        except json.JSONDecodeError:
            print(f"❌ Error: El archivo {filename} tiene un formato JSON inválido")

# ==========================================
# BLOQUE DE EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    ingestor = WebIngestor()
    
    if len(sys.argv) > 1:
        url_objetivo = sys.argv[1]
        institucion_objetivo = sys.argv[2] if len(sys.argv) > 2 else "GENERAL"
        ingestor.scrapear_e_ingestar(url_objetivo, institucion_objetivo)
    else:
        ingestor.procesar_desde_archivo()