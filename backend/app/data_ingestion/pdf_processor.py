import os
import fitz  # PyMuPDF
import sys

# Para importar la base de datos vectorial
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.core.vector_db import vector_db

class PDFToMarkdown:
    def __init__(self, raw_dir="raw_pdfs", output_dir="processed_md"):
        self.raw_dir = os.path.join(os.path.dirname(__file__), raw_dir)
        self.output_dir = os.path.join(os.path.dirname(__file__), output_dir)
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def convert_to_markdown(self, filename):
        pdf_path = os.path.join(self.raw_dir, filename)
        md_filename = filename.replace(".pdf", ".md")
        md_path = os.path.join(self.output_dir, md_filename)
        
        text_content = []
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc):
                # Extraemos el texto de la página
                page_text = page.get_text("text")
                # Añadimos un encabezado de página para ayudar al RAG a ubicarse
                text_content.append(f"## Página {page_num + 1}\n\n{page_text}")
            
            full_md = "\n\n".join(text_content)
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(full_md)
            
            print(f"✅ Convertido: {filename} -> {md_filename}")
            return full_md, md_filename
        
        except Exception as e:
            print(f"❌ Error procesando {filename}: {e}")
            return None, None

    def ingest_to_chroma(self, text, source_name):
        """
        Divide el Markdown en fragmentos (chunks) y los sube a ChromaDB.
        """
        # Dividimos por páginas (usando nuestro marcador ## Página)
        chunks = text.split("## Página")
        texts = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            
            clean_text = f"Fuente: {source_name}\nContenido: {chunk.strip()}"
            texts.append(clean_text)
            metadatas.append({"source": source_name, "type": "pdf_document"})
            ids.append(f"pdf_{source_name}_chunk_{i}")
            
        vector_db.add_documents(texts, metadatas, ids)
        print(f"📦 {source_name} indexado en ChromaDB ({len(texts)} fragmentos)")

    def process_all(self):
        for file in os.listdir(self.raw_dir):
            if file.endswith(".pdf"):
                content, md_name = self.convert_to_markdown(file)
                if content:
                    self.ingest_to_chroma(content, file)

if __name__ == "__main__":
    processor = PDFToMarkdown()
    processor.process_all()