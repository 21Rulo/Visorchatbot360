# ANÁLISIS ARQUITECTÓNICO: SISTEMA MULTIAGENTE LANGGRAPH

## 📋 TABLA DE CONTENIDOS

1. Mapa Conceptual
2. Diagrama de Flujo
3. Responsabilidades de Componentes
4. Estado Compartido
5. Routing & Enrutamiento
6. Dependencias
7. Acoplamientos Detectados
8. Puntos Críticos

---

## 1. MAPA CONCEPTUAL

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CLIENTE FASTAPI                                │
│                   (routes.py - POST /chat)                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                      (MensajeChat)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│           ORQUESTADOR: agente_control.procesar_mensaje()            │
│         Punto de entrada único para toda la lógica multiagente      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
          ┌──────────────────┐  ┌──────────────────┐
          │  LANGGRAPH STATE │  │ MONGODB MEMORY   │
          │  (AgentState)    │  │ (sesiones_chat)  │
          │  - mensaje       │  │ - historial      │
          │  - historial     │  │ - TTL (3 días)   │
          │  - intencion     │  │ - fecha_actividad│
          │  - institucion   │  └──────────────────┘
          │  - query_opt     │
          │  - documentos    │
          │  - respuesta     │
          └──────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
 ┌────────────────┐      ┌─────────────────┐
 │  GRAFO FLUJO   │      │  CHECKPOINTER   │
 │  StateGraph    │      │  MongoDBSaver   │
 │  6 NODOS       │      │  (Persistencia) │
 └────────────────┘      └─────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                    ┌─────────────────────────┐
                    │    NODO 0: CLASIFICADOR │ (LLM)
                    │   (nodo_clasificador)   │
                    │   Groq API - Temp 0.0   │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │ GUIA (0.3%)  │      │ INFO (70%)   │      │ FUERA (26%)  │
    │ Nodo Simple  │      │ RAG PIPELINE │      │ Rápido       │
    └──────────────┘      └──────────────┘      └──────────────┘
          │                      │                      │
          │          ┌───────────┴───────────┐          │
          │          │                       │          │
          ▼          ▼                       ▼          ▼
    ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌──────────────┐
    │NODO1:    │ │NODO2:     │ │NODO3:      │ │NODO4:        │
    │GUIA      │ │ANALISTA   │ │RECUPERADOR │ │FUERA_DOMINIO │
    │nodo_guia │ │IPN        │ │CHROMA      │ │ (singleton)  │
    │          │ │(JSON Mode)│ │(async)     │ │              │
    └──────────┘ └───────────┘ └────────────┘ └──────────────┘
          │          │              │             │
          │          ▼              │             │
          │      ┌────────────────────┐           │
          │      │ NODO 3: SINTESIS   │           │
          │      │ JASPER             │           │
          │      │(nodo_sintesis)     │           │
          │      │Groq API - Temp 0.7 │           │
          │      └────────────────────┘           │
          │                 │                     │
          └─────────────────┼─────────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │ RESPUESTA FINAL │
                    │ → FastAPI       │
                    │ → Cliente       │
                    └─────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

              DEPENDENCIAS EXTERNAS (Singletons)

    ┌────────────────────────────────────────────┐
    │  SharedResources.get_groq_client()         │
    │  (Singleton AsyncGroq)                     │
    │  Modelo: llama-3.3-70b-versatile           │
    └────────────────────────────────────────────┘

    ┌────────────────────────────────────────────┐
    │  vector_db (ChromaManager)                 │
    │  ChromaDB (Persistente)                    │
    │  SentenceTransformer embeddings            │
    │  Instituciones: ESFM, ESIT, ENCB, etc      │
    └────────────────────────────────────────────┘

    ┌────────────────────────────────────────────┐
    │  memory_saver (MongoDBSaver)               │
    │  Checkpoints por thread_id (session_id)    │
    │  Recupera estado en reintentos             │
    └────────────────────────────────────────────┘
```

---

## 2. DIAGRAMA DE FLUJO DETALLADO

```
START
  │
  ├─ [routes.py] POST /chat
  │  ├─ Crea session_id si no existe
  │  ├─ Extrae: mensaje, contexto
  │  └─ Invoca procesar_mensaje()
  │
  ▼
UPDATE MONGODB TTL
  ├─ Marca fecha_ultima_actividad = ahora
  ├─ Configura TTL: 3 días (259200s)
  └─ Si falla: log warning (no bloquea)
  │
  ▼
INVOCAR LANGGRAPH WORKFLOW
  ├─ Carga estado persistente (MongoDB)
  ├─ Inicializa AgentState
  ├─ thread_id = session_id (para checkpointing)
  └─ Comienza ejecución en NODO CLASIFICADOR
  │
  ▼
┌──────────────────────────────────────────────┐
│          NODO 0: CLASIFICADOR                │
│   Entrada: mensaje, contexto_ubicacion      │
│   Salida: intencion (GUIA, INFO, FUERA)     │
│                                              │
│   LÓGICA:                                    │
│   1. Consulta Groq con SUPER PROMPT         │
│   2. Temperatura = 0.0 (max rigidez)        │
│   3. Max tokens = 10 (solo palabra)          │
│   4. Respuesta esperada: UNA categoría       │
│                                              │
│   FALLBACK:                                  │
│   Si error en Groq → intencion = "GUIA"     │
└──────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│   ROUTER: enrutador_de_intencion   │
│   (Función pure - lógica local)    │
└─────────────────────────────────────┘
  │
  ├─── IF "INFO" in intencion
  │    └─→ RAMA RAG PIPELINE
  │
  ├─── IF "FUERA_DOMINIO" in intencion
  │    └─→ NODO FUERA_DOMINIO (directo)
  │
  └─── DEFAULT → RAMA GUIA
       └─→ NODO GUIA (direct)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RAMA 1: GUIA (Conversación general)
  │
  ├─ Entrada: estado con todo
  │  ├─ mensaje
  │  ├─ contexto_ubicacion
  │  ├─ historial (últimos 10 msgs)
  │  └─ No necesita análisis
  │
  ▼
┌──────────────────────────────────────────────┐
│        NODO 1: AGENTE GUÍA                   │
│     (nodo_guia - agente_guia.py)            │
│                                              │
│   REGLAS ESTRICTAS:                         │
│   • No uses markdown (cero formato)         │
│   • Max 30 palabras                         │
│   • Tono: conversacional, joven             │
│   • Eres "Jasper" (nunca digas IA)         │
│   • Contexto actual del usuario             │
│                                              │
│   SALIDA:                                    │
│   respuesta + actualización historial       │
└──────────────────────────────────────────────┘
  │
  ├─ Consulta Groq con SYSTEM PROMPT
  ├─ Temp = 0.7 (algo creativo)
  ├─ Agrega historial anterior
  └─ Maneja groq.RateLimitError
  │
  ▼
END (devuelve respuesta)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RAMA 2: RAG PIPELINE (Información académica)
  │
  ▼
┌──────────────────────────────────────────────┐
│     NODO 2: ANALISTA IPN                     │
│  (nodo_analista_ipn - agente_info.py)       │
│                                              │
│  RESPONSABILIDAD: Query Expansion            │
│  Transforma pregunta vaga en búsqueda rich   │
│                                              │
│  ENTRADA:                                    │
│  • mensaje original                         │
│  • historial últimos 4 msgs                 │
│  • contexto_ubicacion                       │
│                                              │
│  PROCESO:                                    │
│  1. Analiza intención profunda               │
│  2. Expande con sinónimos técnicos           │
│  3. Detecta institución explícita/implícita  │
│  4. Devuelve JSON MODE:                      │
│     {                                        │
│       "consulta_optimizada": "...",          │
│       "institucion": "ESFM|GENERAL|..."     │
│     }                                        │
│                                              │
│  FALLBACK:                                   │
│  Si error → usa mensaje original + GENERAL  │
│                                              │
│  SALIDA:                                     │
│  • query_optimizada                         │
│  • institucion (Enum validado)              │
└──────────────────────────────────────────────┘
  │
  ├─ Groq con JSON mode (temp=0.0)
  ├─ Max tokens = 300 (JSON estructurado)
  └─ Valida institucion con Enum
  │
  ▼
┌──────────────────────────────────────────────┐
│    NODO 3: RECUPERADOR CHROMA                │
│  (nodo_recuperador_chroma - agente_info.py) │
│                                              │
│  RESPONSABILIDAD: Búsqueda Vectorial         │
│  Ejecuta en thread async para no bloquear    │
│                                              │
│  ENTRADA:                                    │
│  • query_optimizada (from analista)         │
│  • institucion (from analista)              │
│                                              │
│  PROCESO:                                    │
│  1. vector_db.search(query, n_results=3)   │
│  2. Filtro por institución (if != GENERAL) │
│  3. ChromaDB retorna top 3 documentos       │
│  4. Concatena documentos con separadores    │
│                                              │
│  EJECUTOR: asyncio.to_thread()              │
│  (ChromaDB search es bloqueante)            │
│                                              │
│  FALLBACK:                                   │
│  "No se encontró información..."            │
│                                              │
│  SALIDA:                                     │
│  documentos_recuperados (string)            │
└──────────────────────────────────────────────┘
  │
  ├─ Busca en ChromaDB localmente
  ├─ Filtra por institución
  └─ Concatena texto para contexto
  │
  ▼
┌──────────────────────────────────────────────┐
│     NODO 4: SÍNTESIS JASPER                  │
│   (nodo_sintesis_jasper - agente_info.py)   │
│                                              │
│  RESPONSABILIDAD: Generación de Respuesta    │
│  Aplicar reglas estrictas del IPN            │
│                                              │
│  ENTRADA:                                    │
│  • documentos_recuperados (contexto RAG)    │
│  • historial completo                       │
│  • mensaje original                         │
│  • contexto_ubicacion                       │
│                                              │
│  PROCESS:                                    │
│  1. System prompt con reglas IPN             │
│  2. Injeta documentos como "fuente verdad"  │
│  3. Agrega historial anterior                │
│  4. Consulta Groq (temp=0.7)                │
│  5. Max tokens = 400 (respuesta clara)      │
│                                              │
│  REGLAS:                                     │
│  • Nunca inventes información                │
│  • Si no hay info → remite a Servicios       │
│  • No uses markdown                         │
│  • Si error → fallback genérico             │
│                                              │
│  SALIDA:                                     │
│  • respuesta final                          │
│  • actualización historial                  │
└──────────────────────────────────────────────┘
  │
  ├─ Groq con historial + documentos
  ├─ Maneja excepciones
  └─ Actualiza historial con new msg
  │
  ▼
END (devuelve respuesta)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RAMA 3: FUERA_DOMINIO (Rechazo)
  │
  ▼
┌──────────────────────────────────────────────┐
│    NODO 5: FUERA_DOMINIO (Singleton)        │
│                                              │
│  RAPIDEZ: NO llama a Groq                   │
│  Respuesta hardcoded                        │
│                                              │
│  MENSAJE:                                    │
│  "Como guía virtual de este recorrido,     │
│   mi conocimiento se enfoca exclusivamente  │
│   en el Instituto Politécnico Nacional..."  │
│                                              │
│  SALIDA:                                     │
│  respuesta + historial actualizado          │
└──────────────────────────────────────────────┘
  │
  ▼
END (devuelve respuesta)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONVERGENCIA Y PERSISTENCIA
  │
  ├─ Los 3 finales (GUIA, SINTESIS, FUERA)
  │  todos retornan respuesta + historial
  │
  ├─ LangGraph checkpointer guarda estado
  │  ├─ thread_id = session_id
  │  ├─ Guarda AgentState completo
  │  └─ En MongoDB (MongoDBSaver)
  │
  ├─ MongoDB también actualiza sesiones_chat
  │  ├─ Último acceso: fecha_ultima_actividad
  │  ├─ TTL: 3 días expira automático
  │  └─ Historial: últimos 10 mensajes
  │
  ▼
RETORNO A FASTAPI
  └─ JSON:
     {
       "respuesta": "...",
       "session_id": "uuid"
     }
  │
  ▼
CLIENTE RECIBE RESPUESTA
```

---

## 3. RESPONSABILIDADES DE COMPONENTES

### 3.1 COMPONENTES CORE (agente_control.py)

#### **nodo_clasificador()**

- **Responsabilidad**: Enrutamiento inteligente
- **Entrada**: mensaje, contexto_ubicacion
- **Lógica**:
  - Llama a Groq con SUPER PROMPT (restrictivo)
  - Categoriza en: GUIA, INFO, FUERA_DOMINIO
  - Temperatura 0.0 (rigidez máxima)
  - Max tokens = 10 (solo palabra)
- **Salida**: intencion (string)
- **Fallback**: "GUIA" si error
- **Costo**: ~1 token Groq
- **Tiempo**: ~200ms promedio

#### **enrutador_de_intencion()** (Pure Function)

- **Responsabilidad**: Lógica local de branching
- **Entrada**: state["intencion"]
- **Lógica**:
  - "INFO" → agente_info pipeline
  - "FUERA_DOMINIO" → nodo_fuera_dominio
  - DEFAULT → agente_guia
- **Salida**: string (nombre de nodo siguiente)
- **Transaccional**: NO (solo lógica)

#### **nodo_fuera_dominio()**

- **Responsabilidad**: Rechazo rápido sin IA
- **Entrada**: cualquier estado
- **Lógica**: Retorna respuesta hardcoded
- **Salida**: respuesta + historial
- **Costo**: 0 tokens (no consume Groq)
- **Patrón**: Singleton (mismo mensaje para todos)

#### **procesar_mensaje()** (Orquestador)

- **Responsabilidad**: Punto de entrada desde FastAPI
- **Entrada**: session_id, mensaje, contexto_ubicacion
- **Lógica**:
  1. Actualiza TTL en MongoDB
  2. Prepara config (thread_id = session_id)
  3. Invoca app_chatbot.ainvoke()
  4. Maneja excepciones críticas
- **Salida**: respuesta (string)
- **Transaccional**: Sí (MongoDB + LangGraph)

### 3.2 COMPONENTES RAG (agente_info.py)

#### **nodo_analista_ipn()**

- **Responsabilidad**: Query Expansion + Extracción de institución
- **Entrada**: mensaje, historial[-4:], contexto_ubicacion
- **Lógica**:
  1. JSON Mode Groq (temp=0.0)
  2. Expande con sinónimos técnicos IPN
  3. Detecta institución (ESFM, ESIT, etc.)
  4. Valida con Enum
- **Salida**: query_optimizada, institucion
- **Fallback**: mensaje original + "GENERAL"
- **Costo**: ~40 tokens Groq
- **Tiempo**: ~500ms

#### **nodo_recuperador_chroma()**

- **Responsabilidad**: Búsqueda vectorial no bloqueante
- **Entrada**: query_optimizada, institucion
- **Lógica**:
  1. asyncio.to_thread() → ChromaDB search
  2. n_results = 3 documentos
  3. Filtro por institución (if != GENERAL)
  4. Concatena documentos con separadores
- **Salida**: documentos_recuperados (string)
- **Fallback**: "No se encontró información..."
- **Costo**: 0 tokens (local)
- **Tiempo**: ~100-300ms

#### **nodo_sintesis_jasper()**

- **Responsabilidad**: Generación contextualizada de respuesta
- **Entrada**: mensaje, documentos_recuperados, historial, contexto_ubicacion
- **Lógica**:
  1. System prompt con reglas IPN (Jasper)
  2. Inyecta documentos como "fuente verdad"
  3. Agrega historial anterior
  4. Groq (temp=0.7, max=400 tokens)
  5. Actualiza historial
- **Salida**: respuesta, historial
- **Fallback**: "Tuve un pequeño problema..."
- **Costo**: ~150 tokens Groq
- **Tiempo**: ~800ms

### 3.3 COMPONENTES GUÍA (agente_guia.py)

#### **nodo_guia()**

- **Responsabilidad**: Conversación directa (sin RAG)
- **Entrada**: mensaje, contexto_ubicacion, historial
- **Lógica**:
  1. System prompt de "Jasper" (guía turístico)
  2. Reglas: max 30 palabras, sin markdown, joven
  3. Agrega historial completo
  4. Groq (temp=0.7, max=400 tokens)
  5. Maneja RateLimitError específicamente
- **Salida**: respuesta, historial
- **Fallback**: Fallback por timeout Groq
- **Costo**: ~80 tokens Groq
- **Tiempo**: ~600ms
- **Patron**: Camino directo (no pipeline)

### 3.4 INFRAESTRUCTURA

#### **Memoria Persistente (checkpointer.py)**

- **Responsabilidad**: Guardar/recuperar estado entre invocaciones
- **Mecanismo**: MongoDBSaver + LangGraph
- **Clave**: thread_id = session_id
- **Contenido guardado**: AgentState completo
- **Recuperación**: Automática en siguientes mensajes
- **Transaccional**: Sí (MongoDB)

#### **Gestión de Sesión (short_term.py)**

- **Responsabilidad**: Operaciones de historial en MongoDB
- **Funciones principales**:
  - obtener_historial(session_id): Recupera últimos 10 msgs
  - agregar_mensaje(session_id, rol, contenido): Añade + trunca
  - limpiar_sesion(session_id): Elimina sesión completa
- **Límite**: MAX_MENSAJES = 10 (últimos 5 interacciones)
- **Índices**: TTL automático (3 días)

#### **Vector DB (vector_db.py)**

- **Responsabilidad**: Almacenamiento y recuperación de embeddings
- **Cliente**: ChromaDB PersistentClient
- **Embeddings**: SentenceTransformer (all-MiniLM-L6-v2)
- **Colección**: "ipn_knowledge"
- **Filtros**: Por institución (ESFM, ESIT, ENCB, etc.)
- **Instancia**: Global singleton

#### **Configuración (config.py)**

- **Responsabilidad**: Settings centralizados y Groq singleton
- **Elementos**:
  - GROQ_API_KEY (env)
  - MODELO_CHAT = "llama-3.3-70b-versatile"
  - MONGO_URI (env)
  - DATABASE_NAME = "visor360_db"
  - SharedResources.get_groq_client() (Singleton)
- **Patrón**: Singleton para evitar múltiples clientes Groq

#### **Utilidades (utils.py)**

- **Responsabilidad**: Reintentos y llamadas centralizadas a Groq
- **Función**: llamar_llm_con_reintentos()
  - Retry logic: exponential backoff
  - Max attempts = 4
  - Maneja groq.RateLimitError
  - Soporta respuestas JSON o texto
  - Ajusta temperatura según formato
- **Patrón**: Decorador @retry de tenacity

#### **Base de Datos (database.py)**

- **Responsabilidad**: Conexión asíncrona a MongoDB Atlas
- **Inicialización**: En lifespan (startup de FastAPI)
- **Finalización**: En lifespan (shutdown de FastAPI)
- **Operaciones**:
  - connect_to_mongo(): Establece conexión + crea índices TTL
  - close_mongo_connection(): Limpia recursos
  - get_db(): Getter para usar en cualquier lugar
- **Instancia**: Singleton MongoDB (db_client)

---

## 4. ESTADO COMPARTIDO (AgentState)

### 4.1 Definición (schemas.py)

```python
class AgentState(TypedDict):
    # ENTRADA
    session_id: str              # UUID único por sesión
    mensaje: str                 # Pregunta del usuario actual
    contexto_ubicacion: str      # Dónde está en el visor 360

    # MEMORIA
    historial: List[Dict]        # Últimos 10 msgs {role, content}
                                 # Función reducer: gestionar_historial()

    # TRANSFORMACIONES INTERMEDIAS (RAG Pipeline)
    intencion: Optional[str]     # GUIA, INFO, FUERA_DOMINIO
    institucion: Optional[str]   # ESFM, ESIT, ENCB, GENERAL, etc.
    query_optimizada: Optional[str]  # Query Expansion del mensaje
    documentos_recuperados: Optional[str]  # Top 3 docs de ChromaDB

    # SALIDA
    respuesta: Optional[str]     # Respuesta final para el cliente
```

### 4.2 Flujo de Estado

```
┌─────────────────────────────────────────┐
│ Estado Inicial (en procesar_mensaje)    │
├─────────────────────────────────────────┤
│ {                                       │
│   session_id: "uuid-xxxx",             │
│   mensaje: "¿Cómo me inscribo?",       │
│   contexto_ubicacion: "ESFM - Aula 1",│
│   historial: [],  ← Vacío o de MongoDB│
│   intencion: None,                     │
│   institucion: None,                   │
│   query_optimizada: None,              │
│   documentos_recuperados: None,        │
│   respuesta: None                      │
│ }                                       │
└─────────────────────────────────────────┘
           ↓ (nodo_clasificador)
┌─────────────────────────────────────────┐
│ {                                       │
│   ... (todo anterior) +                 │
│   intencion: "INFO"  ← Agregado        │
│ }                                       │
└─────────────────────────────────────────┘
           ↓ (enrutador) → RAG PIPELINE
           ↓ (nodo_analista_ipn)
┌─────────────────────────────────────────┐
│ {                                       │
│   ... (todo anterior) +                 │
│   query_optimizada: "inscripción... ", │
│   institucion: "GENERAL"                │
│ }                                       │
└─────────────────────────────────────────┘
           ↓ (nodo_recuperador_chroma)
┌─────────────────────────────────────────┐
│ {                                       │
│   ... (todo anterior) +                 │
│   documentos_recuperados: "Reglamento..│
│                           ...Servicios"│
│ }                                       │
└─────────────────────────────────────────┘
           ↓ (nodo_sintesis_jasper)
┌─────────────────────────────────────────┐
│ {                                       │
│   ... (todo anterior) +                 │
│   respuesta: "Para inscribirte...",    │
│   historial: [{role: "user", ...},     │
│               {role: "assistant", ...}]│
│ }                                       │
└─────────────────────────────────────────┘
           ↓ (retorno)
┌─────────────────────────────────────────┐
│ CLIENTE RECIBE:                         │
│ {                                       │
│   "respuesta": "Para inscribirte...",  │
│   "session_id": "uuid-xxxx"            │
│ }                                       │
└─────────────────────────────────────────┘
```

### 4.3 Fuentes de Datos del Estado

| Campo                    | Origen                           | Cuándo se carga                 |
| ------------------------ | -------------------------------- | ------------------------------- |
| `session_id`             | Cliente (routes.py)              | Siempre                         |
| `mensaje`                | Cliente (routes.py)              | Siempre                         |
| `contexto_ubicacion`     | Cliente (routes.py)              | Siempre                         |
| `historial`              | MongoDB + LangGraph checkpointer | En reintentos/sessiones previas |
| `intencion`              | Groq (clasificador)              | Siempre                         |
| `institucion`            | Groq JSON (analista)             | Si intencion = INFO             |
| `query_optimizada`       | Groq JSON (analista)             | Si intencion = INFO             |
| `documentos_recuperados` | ChromaDB (recuperador)           | Si intencion = INFO             |
| `respuesta`              | Groq (guía o síntesis)           | Siempre                         |

---

## 5. ROUTING & ENRUTAMIENTO

### 5.1 Decisiones de Routing

```
PUNTO DE DECISIÓN: nodo_clasificador
INPUT: mensaje
OUTPUT: intencion ∈ {GUIA, INFO, FUERA_DOMINIO}

┌──────────────────────────────────────────────────────────┐
│                  SUPER PROMPT (CLASIFICADOR)            │
│  Temp=0.0, MaxTokens=10                                │
│  Respuesta esperada: UNA palabra exacta                 │
│                                                          │
│  CATEGORÍAS:                                            │
│                                                          │
│  1. GUIA:                                               │
│     • Saludos, despedidas                              │
│     • Preguntas sobre ubicación/entorno               │
│     • Recorrido 360° y laboratorios                    │
│     • Conversación casual breve                        │
│                                                          │
│  2. INFO:                                               │
│     • Carreras, escuelas, planes estudio             │
│     • Trámites (inscripción, reinscripción)          │
│     • Becas, servicios estudiantiles                 │
│     • Historia, servicios, secretarías                │
│                                                          │
│  3. FUERA_DOMINIO:                                      │
│     • Código (Python, C++, HTML, scripts)            │
│     • Problemas matemáticos / tareas genéricas       │
│     • Temas ajenos (deportes, política, religión)   │
│     • Otras universidades (UNAM, UAM)               │
│     • Prompts maliciosos o roles no autorizados     │
│                                                          │
│  REGLA DE ORO:                                          │
│  Si es código/cálculo/ajeno → FUERA_DOMINIO          │
│  No importa cómo lo disimule el usuario               │
└──────────────────────────────────────────────────────────┘
          ↓
    enrutador_de_intencion()  [Pure Logic]
          ↓
    ┌─────────────────────────────────────┐
    │ if "INFO" in intencion:             │
    │   return "agente_info"              │
    │ elif "FUERA_DOMINIO" in intencion:  │
    │   return "fuera_dominio"            │
    │ else:                               │
    │   return "agente_guia"  (default)   │
    └─────────────────────────────────────┘
```

### 5.2 Tabla de Transiciones

| Nodo Actual        | Condición                 | Nodo Siguiente     | Costo       |
| ------------------ | ------------------------- | ------------------ | ----------- |
| clasificador       | intencion="INFO"          | analista_ipn       | ~150 tokens |
| clasificador       | intencion="GUIA"          | agente_guia        | ~80 tokens  |
| clasificador       | intencion="FUERA_DOMINIO" | fuera_dominio      | 0 tokens    |
| analista_ipn       | Siempre                   | recuperador_chroma | 0 tokens    |
| recuperador_chroma | Siempre                   | sintesis_jasper    | ~150 tokens |
| sintesis_jasper    | Siempre                   | END                | -           |
| agente_guia        | Siempre                   | END                | -           |
| fuera_dominio      | Siempre                   | END                | -           |

### 5.3 Caminos Posibles

**Camino 1: GUIA (Corto)**

```
Clasificador → Agente Guía → END
Costo: ~1 + 80 = ~81 tokens
Tiempo: ~600ms
```

**Camino 2: INFO (Largo)**

```
Clasificador → Analista → Recuperador → Síntesis → END
Costo: ~1 + 40 + 0 + 150 = ~191 tokens
Tiempo: ~1400ms
```

**Camino 3: FUERA_DOMINIO (Rápido)**

```
Clasificador → Fuera Dominio → END
Costo: ~1 + 0 = ~1 token
Tiempo: ~200ms
```

---

## 6. DEPENDENCIAS

### 6.1 Dependencias Externas

```
┌─────────────────────────────────────┐
│    GROQ API (Claude/Llama)         │
│    Endpoint: api.groq.com          │
│                                     │
│ Usado por:                         │
│ • nodo_clasificador (1 call)       │
│ • nodo_analista_ipn (1 call)       │
│ • nodo_guia (1 call)               │
│ • nodo_sintesis_jasper (1 call)    │
│                                     │
│ Total calls posibles: 4/request    │
│ Modelo: llama-3.3-70b-versatile   │
│ Rate limit: Manejado con reintentos│
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│    MONGODB ATLAS                   │
│    Endpoint: MongoDB cloud         │
│                                     │
│ Usado por:                         │
│ • checkpointer (LangGraph)         │
│ • database.py (TTL updates)        │
│ • short_term.py (historial)        │
│                                     │
│ Colecciones:                       │
│ • sesiones_chat                    │
│ • langgraph_checkpoints (internal) │
│                                     │
│ TTL: 3 días automático             │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│    CHROMADB (Local Persistente)    │
│    Path: /home/appuser/chroma_data │
│                                     │
│ Usado por:                         │
│ • nodo_recuperador_chroma          │
│                                     │
│ Colecciones:                       │
│ • ipn_knowledge                    │
│                                     │
│ Embeddings: SentenceTransformer    │
│ Modelo: all-MiniLM-L6-v2           │
│                                     │
│ Operaciones:                       │
│ • search (query, n_results, where) │
│ • upsert (add_documents)           │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│    FASTAPI                         │
│    Endpoint: POST /api/chat        │
│                                     │
│ Entrada: MensajeChat               │
│ Salida: {respuesta, session_id}    │
│                                     │
│ Lifespan:                          │
│ • connect_to_mongo (startup)       │
│ • close_mongo_connection (shutdown)│
└─────────────────────────────────────┘
```

### 6.2 Dependencias Internas (Importes)

```
agente_control.py
├─ from langgraph.graph import StateGraph, END
├─ from app.models.schemas import AgentState
├─ from app.core.config import settings, SharedResources
├─ from app.agents.agente_guia import nodo_guia
├─ from app.agents.agente_info import [3 nodos]
├─ from app.memory.checkpointer import memory_saver
└─ from app.models.database import get_db

agente_info.py
├─ from app.core.config import SharedResources
├─ from app.core.vector_db import vector_db
├─ from app.models.schemas import AgentState, Institucion
└─ from app.core.utils import llamar_llm_con_reintentos

agente_guia.py
├─ from app.core.config import SharedResources
├─ from app.models.schemas import AgentState
├─ from app.core.utils import llamar_llm_con_reintentos
└─ import groq

routes.py
├─ from app.api.routes import MensajeChat (schema)
├─ from app.agents.agente_control import procesar_mensaje
└─ import uuid

vector_db.py
├─ import chromadb
└─ from sentence_transformers import SentenceTransformer

config.py
├─ from dotenv import load_dotenv
└─ from groq import AsyncGroq

database.py
├─ from motor.motor_asyncio import AsyncIOMotorClient
└─ from app.core.config import settings

utils.py
├─ from tenacity import [decoradores]
└─ from app.core.config import settings

checkpointer.py
├─ from pymongo import MongoClient
├─ from langgraph.checkpoint.mongodb import MongoDBSaver
└─ from app.core.config import settings

short_term.py
├─ from app.models.database import get_db
└─ import datetime

main.py (FastAPI)
├─ from app.models.database import [funciones]
├─ from app.api.routes import router
└─ from fastapi.middleware.cors import CORSMiddleware
```

### 6.3 Matriz de Dependencias (Tabla)

| Componente              | Depende de            | Crítico          | Observable               |
| ----------------------- | --------------------- | ---------------- | ------------------------ |
| nodo_clasificador       | Groq API              | SÍ               | Lógica de routing        |
| nodo_guia               | Groq API              | SÍ               | Respuesta conversacional |
| nodo_analista_ipn       | Groq API, Enum        | SÍ               | Extracción institución   |
| nodo_recuperador_chroma | ChromaDB local        | SÍ               | Documentos recuperados   |
| nodo_sintesis_jasper    | Groq API, docs        | SÍ               | Respuesta final          |
| procesar_mensaje        | LangGraph, MongoDB    | SÍ               | Invocación del grafo     |
| checkpointer            | MongoDB               | NO (fallback OK) | Persistencia             |
| memory_saver            | MongoDB, MongoDBSaver | NO               | Recuperación estado      |
| vector_db               | ChromaDB, embeddings  | SÍ               | Base conocimiento        |
| SharedResources         | Groq API key          | SÍ               | Singleton cliente        |

---

## 7. ACOPLAMIENTOS DETECTADOS

### 7.1 Acoplamiento VERTICAL (Espagueti)

```
┌────────────────────────────────────────────────────────┐
│         ACOPLAMIENTO VERTICAL: Estado Compartido      │
└────────────────────────────────────────────────────────┘

AgentState es la "AUTOPISTA" por donde viaja TODO:

nodo_clasificador()
  └─ Escribe: intencion

nodo_analista_ipn()
  ├─ Lee: mensaje, historial, contexto
  └─ Escribe: query_optimizada, institucion

nodo_recuperador_chroma()
  ├─ Lee: query_optimizada, institucion
  └─ Escribe: documentos_recuperados

nodo_sintesis_jasper()
  ├─ Lee: mensaje, documentos, historial, contexto
  └─ Escribe: respuesta, historial

PROBLEMA:
• Cada nodo agrega/consume campos
• No hay validación entre nodos
• Si nodo N falla, nodo N+1 recibe estado INCONSISTENTE
• Cambiar un campo requiere revisar TODOS los nodos
• TypedDict requiere actualización manual
```

### 7.2 Acoplamiento HORIZONTAL (Groq)

```
┌────────────────────────────────────────────────────────┐
│       ACOPLAMIENTO HORIZONTAL: Dependencia Groq       │
└────────────────────────────────────────────────────────┘

TODOS llaman a Groq (excepto recuperador_chroma):

nodo_clasificador()
  └─ Groq: 1 call (temp=0.0, 10 tokens)

nodo_guia()
  └─ Groq: 1 call (temp=0.7, 400 tokens)

nodo_analista_ipn()
  └─ Groq: 1 call (JSON mode, temp=0.0, 300 tokens)

nodo_sintesis_jasper()
  └─ Groq: 1 call (temp=0.7, 400 tokens)

PROBLEMA:
• Si Groq cae → TODA la app cae
• Rate limits afectan todos los nodos
• No hay fallback "degraded mode"
• Costos de tokens dispersos
• Imposible testear sin Groq (mock complejo)
• 4 clientes Groq potenciales (aunque es singleton)

CUELLO DE BOTELLA:
• ~200 ms por call Groq promedio
• 3 calls en rama INFO = 600+ ms latencia
• Altamente sensible a network latency
```

### 7.3 Acoplamiento TEMPORAL (Groq + MongoDB)

```
┌────────────────────────────────────────────────────────┐
│    ACOPLAMIENTO TEMPORAL: Orden de Ejecución         │
└────────────────────────────────────────────────────────┘

procesar_mensaje()
  ├─ 1️⃣ MongoDB UPDATE (TTL)
  │      └─ Si falla: log solo (no bloquea)
  │
  ├─ 2️⃣ LangGraph.ainvoke()
  │      ├─ Carga checkpointer (MongoDB)
  │      │    └─ Si falla: ? (estado vacío?)
  │      │
  │      └─ Ejecuta flujo (4+ Groq calls)
  │          └─ Guarda checkpointer (MongoDB)
  │              └─ Si falla: estado perdido
  │
  └─ 3️⃣ Retorna respuesta
         └─ Cliente recibe

PROBLEMA:
• Dos conexiones MongoDB separadas
• Recuperador de estado vs guardador de estado
• Si mongoDB falla en paso 2.1 → ¿historial perdido?
• Si MongoDB falla en paso 2.2 → ¿siguiente call sin memoria?
• No hay transacciones ACID claras
• Posible inconsistencia entre checkpointer y sesiones_chat
```

### 7.4 Acoplamiento CONCEPTUAL (Arquitectura)

```
┌────────────────────────────────────────────────────────┐
│       ACOPLAMIENTO CONCEPTUAL: Múltiples Roles       │
└────────────────────────────────────────────────────────┘

UN AGENTE = DEMASIADAS RESPONSABILIDADES:

nodo_sintesis_jasper() hace:
  • RAG (inyecta documentos)
  • Formatting (no markdown)
  • Roleplay (soy Jasper)
  • Actualización de historial
  • Manejo de errores
  • Fallbacks

nodo_clasificador() hace:
  • Routing inteligente
  • Categorización
  • Prompt engineering defensivo
  • Manejo de fallbacks

PROBLEMA:
• Single Responsibility Principle violado
• Cambiar regla de Jasper → editar síntesis
• Cambiar clasificación → editar router
• Testing unitario es muy complejo
• Reutilización de lógica es difícil
```

### 7.5 Acoplamiento IMPLÍCITO (Constantes mágicas)

```
┌────────────────────────────────────────────────────────┐
│   ACOPLAMIENTO IMPLÍCITO: Valores Hardcodeados       │
└────────────────────────────────────────────────────────┘

short_term.py:
  MAX_MENSAJES = 10  ← ¿Por qué 10?

utils.py:
  max_tokens=300 (JSON)  ← Variable por contexto
  max_tokens=400 (texto) ← Hardcodeado
  temperature=0.0 / 0.7  ← Implícito en contexto

vector_db.py:
  n_results=3  ← Siempre 3, nunca 2 o 5

agente_info.py:
  "## "  ← Split pattern para chunks
  metadata keys: "institucion" ← Debe coincidir con JSON

routes.py:
  UUID generation  ← Patrón no documentado

config.py:
  DATABASE_NAME = "visor360_db"  ← Nombrado implícitamente

PROBLEMA:
• No hay configuración centralizada
• Cambiar MAX_MENSAJES requiere rebusca en código
• n_results = 3 es misterio (¿por qué no 5?)
• Reglas mágicas dispersas en prompts
```

### 7.6 Tabla Resumen de Acoplamientos

| Tipo                           | Severidad | Afectados              | Impacto                |
| ------------------------------ | --------- | ---------------------- | ---------------------- |
| Estado compartido (AgentState) | ALTA      | Todos los nodos        | Cambios en cascada     |
| Dependencia Groq               | CRÍTICA   | 4/5 nodos              | Outage total           |
| MongoDB dual                   | MEDIA     | checkpointer + TTL     | Inconsistencia posible |
| Orden ejecución                | MEDIA     | procesar_mensaje       | Fallo silencioso       |
| Multi-responsabilidades        | MEDIA     | Síntesis, Clasificador | Testing complejo       |
| Constantes hardcodeadas        | BAJA      | Mantenimiento          | Frágil                 |

---

## 8. PUNTOS CRÍTICOS

### 8.1 Puntos de Fallo Críticos

```
CRÍTICO: nodo_clasificador
├─ Razón: Punto de entrada único
├─ Si falla: TODO falla (router no sabe dónde ir)
├─ Fallback: "GUIA" (default seguro)
├─ Monitorear:
│  • Groq API status
│  • Latencia > 500ms
│  • Respuestas malformadas (no contienen palabra clave)
├─ Recuperación: Reintentos automáticos (tenacity)
└─ SLA esperado: 99% uptime (Groq es upstream)

CRÍTICO: Groq API
├─ Razón: 4 llamadas por request (en worst case)
├─ Si falla: App entera degradada
├─ Síntomas:
│  • Timeouts > 2s
│  • RateLimitError (429)
│  • AuthenticationError (401)
│  • ServerError (500)
├─ Monitorear:
│  • Rate limit headers
│  • Token consumption per request
│  • Error distribution
├─ Recuperación: Retry con exponential backoff (max 4)
└─ SLA esperado: 99.5% (terceros)

CRÍTICO: MongoDB (Persistencia)
├─ Razón: Historial + Checkpointer están aquí
├─ Si falla: Estado perdido en siguiente request
├─ Síntomas:
│  • Connection timeout
│  • Auth error
│  • TTL index corrupted
├─ Monitorear:
│  • Conexión heartbeat
│  • Índices TTL activos
│  • Tamaño colecciones (sesiones_chat crecimiento)
├─ Recuperación:
│  │ Si cae durante UPDATE TTL → log, continúa
│  │ Si cae durante checkpointer → exception → fallback a sin memoria
└─ SLA esperado: 99.9% (Atlas managed)

CRÍTICO: ChromaDB (Embeddings)
├─ Razón: Fuente de verdad para información
├─ Si falla: Rama INFO retorna "No se encontró..."
├─ Síntomas:
│  • Índices corruptos
│  • Vectores duplicados
│  • Filtro por institución no funciona
├─ Monitorear:
│  • Tamaño base datos
│  • Latencia búsqueda
│  • Consistencia embeddings
├─ Recuperación: Reintentos a ChromaDB (asyncio.to_thread)
└─ SLA esperado: 99% (local)
```

### 8.2 Puntos de Carga/Performance

```
CUELLO DE BOTELLA 1: Latencia Groq
├─ Peor caso: 4 calls secuenciales
│  Clasificador (200ms)
│  → Analista (500ms)
│  → Síntesis (800ms)
│  = ~1500ms total
├─ Mejor caso: 1 call (Guía: 600ms)
├─ Mejora posible: Paralelizar llamadas no dependientes
├─ Impacto: Client timeout si > 30s (FastAPI default)
└─ Monitorear: P95, P99 latencias

CUELLO DE BOTELLA 2: ChromaDB Search
├─ Ejecutado en thread (asyncio.to_thread)
├─ Tiempo: 100-300ms (SentenceTransformer embedding)
├─ Escala: Con más documentos, más lento
├─ Monitorear:
│  • Tamaño índice ChromaDB
│  • Query response time
│  • Embedding model cache
└─ Mejora posible: Caching de embeddings frecuentes

CUELLO DE BOTELLA 3: MongoDB Checkpointer
├─ Guardar estado completo por request
├─ Red latency: 50-100ms (Atlas to backend)
├─ Escalabilidad: Linear con número de sesiones
├─ Monitorear:
│  • TTL index efficiency
│  • Replication lag
│  • Query performance
└─ Mejora posible: Batch writes o Redis cache

LÍMITES ACTUALES:
├─ Max concurrent requests: Limited by Groq (RPM)
├─ Max historial: 10 mensajes (MAX_MENSAJES)
├─ Max response time: 30s (FastAPI)
├─ Max tokens per call: 400 (síntesis)
├─ Max ChromaDB results: 3 documentos
└─ MongoDB TTL: 3 días (259200 segundos)
```

### 8.3 Puntos de Decisión Arquitectónica

```
DECISIÓN CRÍTICA 1: Groq Singleton
├─ Actual: SharedResources.get_groq_client() (lazy init)
├─ Ventaja: Una conexión para toda la app
├─ Riesgo: Punto único de fallo (pero sí hay reintentos)
├─ Alternativa: Connection pool (más complejo)
├─ Impacto: Tokens compartidos, rate limits globales
└─ Validez: CORRECTA para current scale

DECISIÓN CRÍTICA 2: MongoDB TTL + Manual Updates
├─ Actual: Índice TTL (3 días) + UPDATE en procesar_mensaje
├─ Ventaja: Limpieza automática, sin garbage collector
├─ Riesgo: Dos operaciones MongoDB separadas = posible inconsistencia
├─ Alternativa: Single transaction o TTL only
├─ Impacto: Sesiones muertas ocupan espacio hasta TTL
└─ Validez: FUNCIONAL pero mejorable

DECISIÓN CRÍTICA 3: ChromaDB Local (No Cloud)
├─ Actual: PersistentClient en /home/appuser/chroma_data
├─ Ventaja: Sin latencia de red, local, rápido
├─ Riesgo: Backups, replication, disaster recovery manual
├─ Alternativa: Pinecone, Weaviate (cloud hosted)
├─ Impacto: Escalabilidad limitada a máquina única
└─ Validez: CORRECTA si esn un solo backend

DECISIÓN CRÍTICA 4: Historial en MongoDB (No LangGraph)
├─ Actual: short_term.py + LangGraph checkpointer dual
├─ Ventaja: Control fino (MAX_MENSAJES = 10)
├─ Riesgo: Duplicación de lógica (gestionar_historial + add_mensaje)
├─ Alternativa: Solo LangGraph checkpointer para estado
├─ Impacto: Código más complejo, 2 fuentes de verdad
└─ Validez: REDUNDANTE, podría simplificarse

DECISIÓN CRÍTICA 5: JSON Mode para Extracción
├─ Actual: nodo_analista_ipn usa Groq JSON mode
├─ Ventaja: Parsing garantizado (Groq asegura JSON válido)
├─ Riesgo: Extra costo de tokens (JSON mode es más caro)
├─ Alternativa: Regex parsing de respuesta texto
├─ Impacto: ~10-20% más tokens, pero garantía de parseo
└─ Validez: CORRECTA por confiabilidad
```

### 8.4 Puntos de Monitoreo Recomendados

```
MÉTRICA 1: Latencia de Request
├─ Óptimo: < 1s (Guía simple)
├─ Aceptable: < 2s (Info con RAG)
├─ Crítico: > 5s
├─ Alertar si: P95 > 2s
└─ Causa probable: Timeout Groq

MÉTRICA 2: Error Rate por Nodo
├─ Clasificador: Target 0%, Crítico > 1%
├─ Analista: Target < 5%, Crítico > 10%
├─ Recuperador: Target 0%, Crítico > 2%
├─ Síntesis: Target < 2%, Crítico > 5%
└─ Fuera Dominio: Target 0%

MÉTRICA 3: Token Consumption
├─ Por request: Promedio ~150-200 tokens
├─ Por sesión: Acumulativo (sin límite)
├─ Alertar si: > 10x promedio en 1 request
└─ Causa probable: Loop infinito o hallucination

MÉTRICA 4: MongoDB Performance
├─ TTL cleanup: Automático cada 60s
├─ Sesiones activas: Monitor crecimiento
├─ Checkpointer writes: Latencia < 100ms
├─ Alertar si: > 200ms latencia
└─ Índices: Validar TTL index existe

MÉTRICA 5: ChromaDB Status
├─ Search latency: < 300ms
├─ Documentos indexados: X total
├─ Filtro institución: % hit rate
├─ Alertar si: Search > 500ms
└─ Posible causa: Índice no optimizado

MÉTRICA 6: Groq API Status
├─ Availability: Target 99.5%
├─ Rate limit consumption: % de cuota
├─ Response time: P95 < 500ms
├─ Error codes: Track 429, 500, 401
├─ Alertar si: 429 errors > 5%
└─ Escalada: Contact Groq support

MÉTRICA 7: Sesiones Activas
├─ Concurrent: Monitor peak
├─ TTL pendientes: Sessions 2+ días old
├─ Reuso rate: % sessions con > 1 message
└─ Alertar si: Memoria MongoDB > 1GB
```

### 8.5 Escenarios de Fallo y Recuperación

```
ESCENARIO 1: Groq API Timeout (nodo_clasificador)
├─ Detección: exception en Groq call
├─ Recuperación: Fallback a "GUIA"
├─ Impacto: User va a rama GUIA (no RAG)
├─ Usuario percibe: Respuesta genérica pero funcional
├─ Log: WARN "[CLASIFICADOR] Error en Groq, fallback GUIA"
└─ Sev: MEDIUM

ESCENARIO 2: ChromaDB Corrupted Index
├─ Detección: Búsqueda retorna 0 resultados siempre
├─ Recuperación: Manual (rebuild index)
├─ Impacto: Rama INFO retorna "No se encontró info"
├─ Usuario percibe: "No sé la respuesta"
├─ Log: ERROR "[RECUPERADOR] ChromaDB unavailable"
├─ Duracion: Minutos a horas (manual)
└─ Sev: HIGH (datos no recuperables)

ESCENARIO 3: MongoDB Connection Lost
├─ Detección: Connection timeout en checkpointer
├─ Recuperación: Reintentos (handled by Motor)
├─ Impacto: Session pierde historial en siguiente call
├─ Usuario percibe: Conversación nueva (amnesia)
├─ Log: ERROR "[CHECKPOINTER] MongoDB unavailable"
├─ Duration: Hasta reconexión
└─ Sev: HIGH

ESCENARIO 4: Groq Rate Limit (429)
├─ Detección: groq.RateLimitError exception
├─ Recuperación: Exponential backoff retry (max 4 intentos)
├─ Impacto: Request se demora 10+ segundos
├─ Usuario percibe: Lento pero funcional
├─ Log: WARN "[LLM] Rate limit hit, retry 2/4"
├─ Duration: Segundos a minutos
└─ Sev: MEDIUM

ESCENARIO 5: Groq hallucination (non-JSON response)
├─ Detección: json.loads() falla en nodo_analista
├─ Recuperación: Fallback a (original_msg, "GENERAL")
├─ Impacto: Query expansion skipped, búsqueda genérica
├─ Usuario percibe: Respuesta menos relevante
├─ Log: WARN "[ANALISTA] JSON parse error, using fallback"
├─ Duration: Transparente
└─ Sev: LOW

ESCENARIO 6: LangGraph State Corruption
├─ Detección: KeyError en nodo siguiente (campo faltante)
├─ Recuperación: Exception handler (try/except en cada nodo)
├─ Impacto: Nodo actual genera fallback, flujo continúa
├─ Usuario percibe: Respuesta parcial o genérica
├─ Log: ERROR "[NODO] State corruption, field missing"
├─ Duration: Transparente
└─ Sev: LOW (pero indica bug)

ESCENARIO 7: Network Partition (Backend ↔ Groq)
├─ Detección: Connection refused / Timeout
├─ Recuperación: Retry con backoff (up to 4 attempts)
├─ Impacto: Todo request falla después de max retries
├─ Usuario percibe: "Problema técnico" (generic error)
├─ Log: CRITICAL "[GROQ] Network unreachable"
├─ Duration: hasta fix (manual recovery)
└─ Sev: CRITICAL

ESCENARIO 8: Memory Leak (session accumulation)
├─ Detección: MongoDB sesiones_chat size grows unbounded
├─ Root cause: TTL index not working / corrupted
├─ Recovery: Manual index rebuild + cleanup
├─ Impact: DB slowdown, costs increase
├─ Duration: Hours to days
└─ Sev: MEDIUM (creeping issue)
```

---

## 9. RESUMEN EJECUTIVO

### 9.1 Arquitectura en Palabras

**Un sistema multiagente basado en LangGraph** que:

1. **Clasifica** cada mensaje entrante (Guía vs Info vs Fuera de dominio)
2. **Enruta** a uno de 3 caminos:
   - Guía directa (conversación simple) → 600ms
   - Pipeline RAG (búsqueda + síntesis) → 1500ms
   - Rechazo rápido (no aplica) → 200ms
3. **Persiste** estado en MongoDB (historial + checkpoints)
4. **Recupera** documentos de ChromaDB local
5. **Genera** respuestas con Groq LLM
6. **Expone** vía FastAPI REST

### 9.2 Fortalezas

| Aspecto                | Fortaleza                            |
| ---------------------- | ------------------------------------ |
| Separación de concerns | 6 nodos especializados               |
| Routing inteligente    | Clasificación previa a Groq          |
| Memoria persistente    | MongoDB + LangGraph checkpointer     |
| Recuperación de fallos | Reintentos, fallbacks en cada nodo   |
| Performance RAG        | ChromaDB local, embeddings cacheados |
| Extensibilidad         | Agregar nodos es straightforward     |

### 9.3 Debilidades (Acoplamientos)

| Aspecto           | Debilidad                               |
| ----------------- | --------------------------------------- |
| Estado compartido | AgentState muy acoplado                 |
| Dependencia Groq  | 4 llamadas, punto único fallo           |
| Responsabilidades | Multi-role en nodos grandes             |
| Configuración     | Valores hardcodeados dispersos          |
| Testabilidad      | Mocks complejos por Groq                |
| Escalabilidad     | ChromaDB local no distribuído           |
| Duplicación       | short_term.py + checkpointer redundante |

### 9.4 Recomendaciones ANTES de Migración

1. **Centralizar configuración** (crear `settings.yaml` o env vars)
2. **Extraer constantes** (MAX_MENSAJES, n_results, max_tokens, etc.)
3. **Documentar prompts** en archivos separados (no incrustados)
4. **Crear interfaces claras** para nodos (entrada/salida esperada)
5. **Simplificar estado** (reducer functions claras)
6. **Preparar tests** antes de refactor (regression protection)
7. **Mapear dependencias** de Groq (considerar caché/fallback)
