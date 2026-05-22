import os
import fitz
import sys

# Para importar la base de datos vectorial
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.core.vector_db import vector_db

# Mapeo de variaciones de nombres a instituciones oficiales
INSTITUCION_MAP = {
    "ciitec": "CIITEC",
    "cmpl": "CMPL",
    "encb": "ENCB",
    "encbc": "ENCB",
    "esfm": "ESFM",
    "esimez": "ESIMEZ",
    "esit": "ESIT",
    "udibi": "UDIBI",
}

def inferir_institucion(nombre_archivo, institucion_param=None):
    """
    Infiere la institución desde el nombre del archivo o usa el parámetro proporcionado.
    
    Args:
        nombre_archivo: Nombre del PDF o MD (ej: "ENCB_servicios.pdf")
        institucion_param: Institución pasada como parámetro (ej: "ENCB")
    
    Returns:
        Nombre de la institución en mayúsculas (ej: "ENCB")
    """
    # Si se pasó la institución como parámetro, úsala
    if institucion_param:
        institucion_normalizada = institucion_param.lower()
        return INSTITUCION_MAP.get(institucion_normalizada, institucion_param.upper())
    
    # Si no, intenta inferir del nombre del archivo
    nombre_sin_ext = os.path.splitext(nombre_archivo)[0].lower()
    
    # Busca coincidencias en el nombre del archivo
    for clave, institucion in INSTITUCION_MAP.items():
        if clave in nombre_sin_ext:
            return institucion
    
    # Si no se puede inferir, retorna DESCONOCIDA
    print(f"⚠️  No se pudo inferir institución de '{nombre_archivo}'. Usando 'DESCONOCIDA'")
    return "DESCONOCIDA"

class DataIngestor:
    def __init__(self, raw_dir="raw_pdfs", output_dir="processed_md"):
        self.raw_dir = os.path.join(os.path.dirname(__file__), raw_dir)
        self.output_dir = os.path.join(os.path.dirname(__file__), output_dir)
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def convert_pdf_to_markdown(self, filename):
        pdf_path = os.path.join(self.raw_dir, filename)
        md_filename = filename.replace(".pdf", ".md")
        md_path = os.path.join(self.output_dir, md_filename)
        
        text_content = []
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc):
                page_text = page.get_text("text")
                text_content.append(f"## Página {page_num + 1}\n\n{page_text}")
            
            full_md = "\n\n".join(text_content)
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(full_md)
            
            print(f"✅ PDF Convertido: {filename} -> {md_filename}")
            return full_md, md_filename
        
        except Exception as e:
            print(f"❌ Error procesando PDF {filename}: {e}")
            return None, None

    def read_manual_markdown(self, filename):
        """Lee un archivo .md creado manualmente desde processed_md"""
        md_path = os.path.join(self.output_dir, filename)
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"✅ Markdown manual leído: {filename}")
            return content
        except Exception as e:
            print(f"❌ Error leyendo MD {filename}: {e}")
            return None

    def ingest_to_chroma(self, text, source_name, institucion=None):
        """Divide el Markdown en fragmentos por tamaño y los sube a ChromaDB."""
        
        # Inferir institución si no se proporciona
        if institucion is None:
            institucion = inferir_institucion(source_name)
            
        # 1. Limpiamos las marcas de página que rompen el contexto
        import re
        texto_limpio = re.sub(r'## Página \d+', '', text)
        
        # 2. Separamos por párrafos reales (doble salto de línea)
        parrafos = texto_limpio.split("\n\n")
        
        chunks = []
        chunk_actual = ""
        max_caracteres = 800 # Tamaño ideal para que Jasper lo entienda rápido
        
        # 3. Agrupamos párrafos hasta llegar al límite de caracteres
        for p in parrafos:
            p_limpio = p.strip()
            if not p_limpio:
                continue
                
            if len(chunk_actual) + len(p_limpio) < max_caracteres:
                chunk_actual += p_limpio + "\n\n"
            else:
                if chunk_actual:
                    chunks.append(chunk_actual.strip())
                chunk_actual = p_limpio + "\n\n"
        
        if chunk_actual:
            chunks.append(chunk_actual.strip())

        # 4. Preparamos para ChromaDB
        texts = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Inyectamos el contexto de qué trata este documento en CADA fragmento
            nombre_limpio = source_name.replace('.md', '').replace('.pdf', '')
            clean_text = f"Documento: {nombre_limpio} ({institucion})\nContenido:\n{chunk}"
            
            texts.append(clean_text)
            
            doc_type = "pdf_document" if source_name.endswith('.pdf') else "manual_md"
            metadatas.append({
                "source": source_name,
                "type": doc_type,
                "institucion": institucion
            })
            ids.append(f"doc_{source_name}_chunk_{i}")
            
        if texts:
            vector_db.add_documents(texts, metadatas, ids)
            print(f"📦 {source_name} indexado en ChromaDB ({len(texts)} fragmentos inteligentes) | Institución: {institucion}")

    def process_all_pdfs(self):
        print("Procesando todos los PDFs en la carpeta raw_pdfs...")
        for file in os.listdir(self.raw_dir):
            if file.endswith(".pdf"):
                content, md_name = self.convert_pdf_to_markdown(file)
                if content:
                    institucion = inferir_institucion(file)
                    self.ingest_to_chroma(content, file, institucion)

if __name__ == "__main__":
    ingestor = DataIngestor()
    
    # Manejo de argumentos por consola
    if len(sys.argv) > 1:
        archivo_especifico = sys.argv[1]
        institucion_param = sys.argv[2] if len(sys.argv) > 2 else None
        
        # Si el usuario pide un PDF
        if archivo_especifico.endswith(".pdf"):
            print(f"Procesando únicamente el PDF: {archivo_especifico}")
            if institucion_param:
                print(f"  Institución especificada: {institucion_param}")
            content, md_name = ingestor.convert_pdf_to_markdown(archivo_especifico)
            if content:
                institucion = inferir_institucion(archivo_especifico, institucion_param)
                ingestor.ingest_to_chroma(content, archivo_especifico, institucion)
                
        # Si el usuario pide un Markdown manual
        elif archivo_especifico.endswith(".md"):
            print(f"Procesando únicamente el Markdown: {archivo_especifico}")
            if institucion_param:
                print(f"  Institución especificada: {institucion_param}")
            content = ingestor.read_manual_markdown(archivo_especifico)
            if content:
                institucion = inferir_institucion(archivo_especifico, institucion_param)
                ingestor.ingest_to_chroma(content, archivo_especifico, institucion)
        else:
            print("Formato no soportado. Usa un .pdf o un .md")
            print(f"\nUso:")
            print(f"  python pdf_processor.py archivo.pdf                  # Infiere institución del nombre")
            print(f"  python pdf_processor.py archivo.pdf ENCB             # Usa ENCB como institución")
            print(f"  python pdf_processor.py archivo.md CMPL              # Usa CMPL como institución")
            
    # Si no se mandan argumentos, procesa todos los PDFs por defecto
    else:
        ingestor.process_all_pdfs()