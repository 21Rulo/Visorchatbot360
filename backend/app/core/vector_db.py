import os
import chromadb
from sentence_transformers import SentenceTransformer

class ChromaManager:
    def __init__(self):
        # Definir la ruta donde ChromaDB guardará los datos localmente
        db_path = "/home/appuser/chroma_data"
        
        # Inicializar cliente persistente
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Crear o recuperar la colección (tabla) para el conocimiento del IPN
        self.collection = self.client.get_or_create_collection(name="ipn_knowledge")
        
        # Cargar el modelo de embeddings localmente (se descargará la primera vez)
        print("Cargando modelo de embeddings all-MiniLM-L6-v2...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Modelo cargado exitosamente.")

    def add_documents(self, texts: list[str], metadatas: list[dict], ids: list[str]):
        """Vectoriza y guarda una lista de textos en ChromaDB."""
        if not texts:
            return
        
        # Generar los embeddings matemáticos
        embeddings = self.model.encode(texts).tolist()
        
        # Guardar en ChromaDB
        self.collection.upsert(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, n_results: int = 3, institucion: str = None):
        """
        Busca los fragmentos más relevantes para una pregunta.
        
        Args:
            query: La pregunta o consulta del usuario
            n_results: Número de fragmentos a retornar (default: 3)
            institucion: Filtrar resultados por institución (ej: "ENCB", "CMPL"). 
                        Si es None, busca en todas las instituciones.
        
        Returns:
            Resultados de ChromaDB con documentos, metadatos y distancias
        """
        query_embedding = self.model.encode([query]).tolist()
        
        # Construir filtro si se especifica institución
        where_filter = None
        if institucion:
            where_filter = {"institucion": institucion}
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_filter
        )
        return results

# Instancia global para usar en toda la app
vector_db = ChromaManager()