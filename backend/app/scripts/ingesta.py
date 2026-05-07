import os
import json
import sys

# Ajustar el path para poder importar módulos de la app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.vector_db import vector_db


def agregar_texto(texts, metadatas, ids, texto, metadata, doc_id):
    """
    Agrega texto únicamente si contiene información válida.
    """

    if texto and isinstance(texto, str) and texto.strip():

        texts.append(texto.strip())
        metadatas.append(metadata)
        ids.append(doc_id)


def procesar_jsons_a_chroma():

    kb_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "knowledge_base"
    )

    texts = []
    metadatas = []
    ids = []

    # Leer todos los JSON
    for filename in os.listdir(kb_path):

        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(kb_path, filename)

        institucion = filename.replace(".json", "").upper()

        print(f"Procesando: {filename}")

        try:

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

        except json.JSONDecodeError:
            print(f"❌ Error leyendo JSON: {filename}")
            continue

        except Exception as e:
            print(f"❌ Error inesperado en {filename}: {e}")
            continue

        # =========================================================
        # INSTITUCIÓN
        # =========================================================

        institucion_data = data.get("institucion", {})

        descripcion = institucion_data.get("descripcion")
        agregar_texto(
            texts,
            metadatas,
            ids,
            f"Descripción de {institucion}: {descripcion}",
            {
                "institucion": institucion,
                "tipo": "descripcion"
            },
            f"{institucion}_descripcion"
        )

        mision = institucion_data.get("mision")
        agregar_texto(
            texts,
            metadatas,
            ids,
            f"Misión de {institucion}: {mision}",
            {
                "institucion": institucion,
                "tipo": "mision"
            },
            f"{institucion}_mision"
        )

        vision = institucion_data.get("vision")
        agregar_texto(
            texts,
            metadatas,
            ids,
            f"Visión de {institucion}: {vision}",
            {
                "institucion": institucion,
                "tipo": "vision"
            },
            f"{institucion}_vision"
        )

        historia = institucion_data.get("historia")
        agregar_texto(
            texts,
            metadatas,
            ids,
            f"Historia de {institucion}: {historia}",
            {
                "institucion": institucion,
                "tipo": "historia"
            },
            f"{institucion}_historia"
        )

        ubicacion = institucion_data.get("ubicacion")
        agregar_texto(
            texts,
            metadatas,
            ids,
            f"Ubicación de {institucion}: {ubicacion}",
            {
                "institucion": institucion,
                "tipo": "ubicacion"
            },
            f"{institucion}_ubicacion"
        )

        titular = institucion_data.get("titular")
        agregar_texto(
            texts,
            metadatas,
            ids,
            f"Titular de {institucion}: {titular}",
            {
                "institucion": institucion,
                "tipo": "titular"
            },
            f"{institucion}_titular"
        )

        # =========================================================
        # PROGRAMAS ACADÉMICOS
        # =========================================================

        programas = data.get("programasAcademicos", [])

        for i, programa in enumerate(programas):

            nombre = programa.get("nombre", "Sin nombre")
            descripcion = programa.get("descripcion", "")
            duracion = programa.get("duracion", "No especificada")
            modalidad = programa.get("modalidad", "No especificada")

            texto_programa = f"""
            Programa académico: {nombre}

            Descripción:
            {descripcion}

            Duración:
            {duracion} semestres

            Modalidad:
            {modalidad}
            """

            agregar_texto(
                texts,
                metadatas,
                ids,
                texto_programa,
                {
                    "institucion": institucion,
                    "tipo": "programa_academico",
                    "nombre_programa": nombre
                },
                f"{institucion}_programa_{i}"
            )

        # =========================================================
        # LABORATORIOS
        # =========================================================

        laboratorios = data.get("laboratorios", [])

        for i, lab in enumerate(laboratorios):

            nombre = lab.get("nombre", "Sin nombre")
            descripcion = lab.get("descripcion", "")
            encargado = lab.get("encargado", "No especificado")

            texto_lab = f"""
            Laboratorio: {nombre}

            Descripción:
            {descripcion}

            Encargado:
            {encargado}
            """

            agregar_texto(
                texts,
                metadatas,
                ids,
                texto_lab,
                {
                    "institucion": institucion,
                    "tipo": "laboratorio",
                    "nombre_laboratorio": nombre
                },
                f"{institucion}_laboratorio_{i}"
            )

        # =========================================================
        # NODOS / RECORRIDO VIRTUAL
        # =========================================================

        nodos = data.get("nodos", {})

        for nodo_id, nodo in nodos.items():

            titulo = nodo.get("titulo", "Sin título")
            contexto = nodo.get("contexto_ia", "")

            texto_nodo = f"""
            Lugar: {titulo}

            Contexto:
            {contexto}
            """

            agregar_texto(
                texts,
                metadatas,
                ids,
                texto_nodo,
                {
                    "institucion": institucion,
                    "tipo": "nodo",
                    "nodo_id": nodo_id,
                    "titulo": titulo
                },
                f"{institucion}_{nodo_id}"
            )

    # =========================================================
    # GUARDAR EN CHROMADB
    # =========================================================

    if texts:

        print(f"\n📦 Vectorizando {len(texts)} documentos...")

        vector_db.add_documents(
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )

        print("✅ Ingesta RAG completada con éxito.")

    else:
        print("⚠️ No se encontró información para vectorizar.")


if __name__ == "__main__":
    procesar_jsons_a_chroma()