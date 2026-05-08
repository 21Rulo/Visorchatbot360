import os
import fitz  # PyMuPDF
import sys

# Para importar la base de datos vectorial
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.core.vector_db import vector_db

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

    def ingest_to_chroma(self, text, source_name):
        """Divide el Markdown en fragmentos (chunks) y los sube a ChromaDB."""
        # Si es un PDF, dividimos por páginas. Si es un MD manual, dividimos por encabezados dobles (##)
        chunks = text.split("## ")
        texts = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            
            clean_text = f"Fuente: {source_name}\nContenido: {chunk.strip()}"
            texts.append(clean_text)
            # Etiquetamos el tipo de documento
            doc_type = "pdf_document" if source_name.endswith('.pdf') else "manual_md"
            metadatas.append({"source": source_name, "type": doc_type})
            ids.append(f"doc_{source_name}_chunk_{i}")
            
        vector_db.add_documents(texts, metadatas, ids)
        print(f"📦 {source_name} indexado en ChromaDB ({len(texts)} fragmentos)")

    def process_all_pdfs(self):
        print("Procesando todos los PDFs en la carpeta raw_pdfs...")
        for file in os.listdir(self.raw_dir):
            if file.endswith(".pdf"):
                content, md_name = self.convert_pdf_to_markdown(file)
                if content:
                    self.ingest_to_chroma(content, file)

if __name__ == "__main__":
    ingestor = DataIngestor()
    
    # Manejo de argumentos por consola
    if len(sys.argv) > 1:
        archivo_especifico = sys.argv[1]
        
        # Si el usuario pide un PDF
        if archivo_especifico.endswith(".pdf"):
            print(f"Procesando únicamente el PDF: {archivo_especifico}")
            content, md_name = ingestor.convert_pdf_to_markdown(archivo_especifico)
            if content:
                ingestor.ingest_to_chroma(content, archivo_especifico)
                
        # Si el usuario pide un Markdown manual
        elif archivo_especifico.endswith(".md"):
            print(f"Procesando únicamente el Markdown: {archivo_especifico}")
            content = ingestor.read_manual_markdown(archivo_especifico)
            if content:
                ingestor.ingest_to_chroma(content, archivo_especifico)
        else:
            print("Formato no soportado. Usa un .pdf o un .md")
            
    # Si no se mandan argumentos, procesa todos los PDFs por defecto
    else:
        ingestor.process_all_pdfs()