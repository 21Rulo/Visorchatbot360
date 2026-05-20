# DIAGRAMAS VISUALES - ARQUITECTURA MULTIAGENTE

## 1. DIAGRAMA DE COMPONENTES

```mermaid
graph TB
    subgraph "Cliente"
        CLI["📱 FastAPI Client<br/>(POST /api/chat)"]
    end

    subgraph "API Gateway"
        ROUTES["routes.py<br/>MensajeChat validator"]
    end

    subgraph "Orquestador"
        PROC["procesar_mensaje()"]
        WORKFLOW["LangGraph Workflow<br/>(StateGraph)"]
    end

    subgraph "Nodos de Decisión"
        CLASS["🎯 Clasificador<br/>(Groq)"]
        ROUTER["📍 Router<br/>(Logic)"]
    end

    subgraph "Rama GUÍA"
        GUIA["💬 Agente Guía<br/>(Groq Temp=0.7)"]
    end

    subgraph "Rama RAG (INFO)"
        ANALIST["🧠 Analista IPN<br/>(Groq JSON)"]
        RECUP["🔍 Recuperador<br/>(ChromaDB)"]
        SINTESIS["✨ Síntesis Jasper<br/>(Groq Temp=0.7)"]
    end

    subgraph "Rama FUERA_DOMINIO"
        FUERA["⛔ Fuera Dominio<br/>(Hardcoded)"]
    end

    subgraph "Persistencia"
        MONGO[("🗄️ MongoDB Atlas<br/>(sesiones_chat)<br/>TTL=3d")]
        LANGCHECK["🔐 LangGraph Checkpointer<br/>(MongoDBSaver)"]
    end

    subgraph "Base de Conocimiento"
        CHROMA[("📚 ChromaDB Local<br/>(ipn_knowledge)<br/>SentenceTransformer")]
    end

    subgraph "Recursos Externos"
        GROQ["☁️ Groq API<br/>(llama-3.3-70b)"]
        CONFIG["⚙️ Config<br/>(SharedResources)"]
    end

    CLI -->|MensajeChat| ROUTES
    ROUTES -->|session_id, mensaje, contexto| PROC
    PROC -->|TTL update| MONGO
    PROC -->|load state| LANGCHECK
    PROC -->|invoke| WORKFLOW
    WORKFLOW -->|START| CLASS
    CLASS -->|query Groq| GROQ
    CLASS -->|save intencion| WORKFLOW
    CLASS -->|route| ROUTER

    ROUTER -->|"INFO"| ANALIST
    ROUTER -->|"GUIA"| GUIA
    ROUTER -->|"FUERA"| FUERA

    ANALIST -->|query Groq| GROQ
    ANALIST -->|save query_opt| WORKFLOW
    ANALIST --> RECUP
    RECUP -->|search| CHROMA
    RECUP -->|save docs| WORKFLOW
    RECUP --> SINTESIS
    SINTESIS -->|query Groq| GROQ
    SINTESIS -->|save respuesta| WORKFLOW

    GUIA -->|query Groq| GROQ
    GUIA -->|save respuesta| WORKFLOW

    FUERA -->|hardcoded| WORKFLOW

    WORKFLOW -->|save state| LANGCHECK
    LANGCHECK -->|persist| MONGO
    WORKFLOW -->|respuesta| PROC
    PROC -->|JSON response| CLI

    GROQ -.->|config| CONFIG
    CHROMA -.->|embeddings| GROQ

    style CLASS fill:#ff9800,color:#000
    style ROUTER fill:#4caf50,color:#fff
    style GUIA fill:#2196f3,color:#fff
    style ANALIST fill:#9c27b0,color:#fff
    style RECUP fill:#f44336,color:#fff
    style SINTESIS fill:#ff5722,color:#fff
    style FUERA fill:#673ab7,color:#fff
    style MONGO fill:#ffc107,color:#000
    style CHROMA fill:#ffc107,color:#000
    style GROQ fill:#ff5722,color:#fff
```

---

## 2. DIAGRAMA DE FLUJO DE DATOS

```mermaid
stateDiagram-v2
    [*] --> INPUT: Entrada
    INPUT: session_id, mensaje, contexto_ubicacion

    INPUT --> LOAD_STATE
    LOAD_STATE: Cargar historial de MongoDB

    LOAD_STATE --> INIT_STATE
    INIT_STATE: Inicializar AgentState TypedDict

    INIT_STATE --> CLASSIFY
    CLASSIFY: nodo_clasificador() → Groq temp=0.0

    CLASSIFY --> ROUTE: {intencion: GUIA|INFO|FUERA}

    ROUTE --> GUIA_PATH: Si "GUIA"
    ROUTE --> INFO_PATH: Si "INFO"
    ROUTE --> FUERA_PATH: Si "FUERA_DOMINIO"

    state GUIA_PATH {
        [*] --> GUIA_NODE
        GUIA_NODE: nodo_guia() → Groq temp=0.7
        GUIA_NODE --> STATE_UPDATE_1: Agregar respuesta + historial
        STATE_UPDATE_1 --> [*]
    }

    state INFO_PATH {
        [*] --> ANALYZE
        ANALYZE: nodo_analista_ipn() → Groq JSON
        ANALYZE --> STATE_UPDATE_A: query_optimizada, institucion
        STATE_UPDATE_A --> RETRIEVE
        RETRIEVE: nodo_recuperador_chroma() → ChromaDB
        RETRIEVE --> STATE_UPDATE_R: documentos_recuperados
        STATE_UPDATE_R --> SYNTHESIZE
        SYNTHESIZE: nodo_sintesis_jasper() → Groq temp=0.7
        SYNTHESIZE --> STATE_UPDATE_S: respuesta + historial
        STATE_UPDATE_S --> [*]
    }

    state FUERA_PATH {
        [*] --> REJECT
        REJECT: nodo_fuera_dominio() → Hardcoded
        REJECT --> STATE_UPDATE_F: respuesta + historial
        STATE_UPDATE_F --> [*]
    }

    GUIA_PATH --> PERSIST
    INFO_PATH --> PERSIST
    FUERA_PATH --> PERSIST

    PERSIST: Guardar checkpointer en MongoDB
    PERSIST --> TTL_UPDATE
    TTL_UPDATE: Actualizar fecha_ultima_actividad

    TTL_UPDATE --> RETURN
    RETURN: Retornar {respuesta, session_id}
    RETURN --> [*]
```

---

## 3. DIAGRAMA DE DEPENDENCIAS

```mermaid
graph LR
    subgraph "Groq API (☁️)"
        GROQ["llama-3.3-70b-versatile<br/>Rate Limited<br/>Pay per token"]
    end

    subgraph "MongoDB Atlas (☁️)"
        MONGO["Cluster IPN<br/>sesiones_chat collection<br/>TTL Index<br/>Async Motor"]
    end

    subgraph "ChromaDB (Local)"
        CHROMA["ipn_knowledge collection<br/>SentenceTransformer<br/>Persistent:/home/appuser"]
    end

    subgraph "Backend Python"
        CONFIG["Config + Singletons<br/>SharedResources<br/>Settings"]

        UTIL["utils.py<br/>llamar_llm_con_reintentos<br/>@retry decorator<br/>tenacity"]

        VECTOR["vector_db.py<br/>ChromaManager<br/>add_documents<br/>search"]

        CLASSIFY["nodo_clasificador<br/>Groq call<br/>Fallback:GUIA"]

        GUIA["nodo_guia<br/>Groq call<br/>Fallback generic"]

        ANALIST["nodo_analista_ipn<br/>Groq JSON<br/>Institucion enum"]

        RECUP["nodo_recuperador_chroma<br/>asyncio.to_thread<br/>Fallback text"]

        SINTESIS["nodo_sintesis_jasper<br/>Groq call<br/>Fallback generic"]

        DB["database.py<br/>connect_to_mongo<br/>close_mongo<br/>get_db"]

        CHECKPT["checkpointer.py<br/>MongoDBSaver<br/>Persist state"]

        SHORTTERM["short_term.py<br/>obtener_historial<br/>agregar_mensaje<br/>limpiar_sesion"]

        GRAFO["agente_control.py<br/>StateGraph<br/>LangGraph workflow<br/>procesar_mensaje"]

        ROUTES["routes.py<br/>POST /api/chat<br/>MensajeChat"]
    end

    GROQ -->|1️⃣ query| CLASSIFY
    GROQ -->|2️⃣ query| GUIA
    GROQ -->|3️⃣ query| ANALIST
    GROQ -->|4️⃣ query| SINTESIS

    CLASSIFY -->|calls| UTIL
    GUIA -->|calls| UTIL
    ANALIST -->|calls| UTIL
    SINTESIS -->|calls| UTIL

    UTIL -->|retry logic| GROQ

    CLASSIFY -->|reads| CONFIG
    GUIA -->|reads| CONFIG
    ANALIST -->|reads| CONFIG
    SINTESIS -->|reads| CONFIG
    RECUP -->|reads| CONFIG

    CONFIG -->|singleton| GROQ

    RECUP -->|search| CHROMA
    RECUP -->|calls| VECTOR

    VECTOR -->|persistent| CHROMA

    MONGO -->|TTL index| SHORTTERM

    DB -->|async| MONGO
    CHECKPT -->|save/load| MONGO
    SHORTTERM -->|query| DB

    GRAFO -->|orchestrate| CLASSIFY
    GRAFO -->|orchestrate| GUIA
    GRAFO -->|orchestrate| ANALIST
    GRAFO -->|orchestrate| RECUP
    GRAFO -->|orchestrate| SINTESIS

    GRAFO -->|checkpointer| CHECKPT
    GRAFO -->|config| CONFIG

    ROUTES -->|invoke| GRAFO

    style GROQ fill:#ff5722,stroke:#000,stroke-width:3px
    style MONGO fill:#ffc107,stroke:#000,stroke-width:2px
    style CHROMA fill:#4caf50,stroke:#000,stroke-width:2px
    style CLASSIFY fill:#ff9800
    style GUIA fill:#2196f3
    style ANALIST fill:#9c27b0
    style RECUP fill:#f44336
    style SINTESIS fill:#ff5722
```

---

## 4. DIAGRAMA DE CICLO DE VIDA

```mermaid
sequenceDiagram
    participant User as 👤 Cliente
    participant FastAPI as 🌐 FastAPI
    participant Control as 🎛️ agente_control
    participant Grafo as 📊 LangGraph
    participant Groq as ☁️ Groq API
    participant MongoDB as 🗄️ MongoDB
    participant ChromaDB as 📚 ChromaDB

    User->>FastAPI: POST /api/chat {mensaje, contexto}

    FastAPI->>Control: procesar_mensaje(session_id, msg, ctx)

    Control->>MongoDB: UPDATE fecha_ultima_actividad (TTL)
    MongoDB-->>Control: OK

    Control->>Grafo: ainvoke(inputs, config={thread_id})

    Grafo->>MongoDB: Load checkpointer
    MongoDB-->>Grafo: State (or empty)

    Grafo->>Grafo: ENTRY → nodo_clasificador

    Grafo->>Groq: query(mensaje) [temp=0.0, max=10]
    Groq-->>Grafo: "INFO" (or GUIA, FUERA)

    alt intencion = INFO
        Grafo->>Grafo: ROUTE → analista_ipn

        Grafo->>Groq: expand_query(msg, hist) [JSON mode]
        Groq-->>Grafo: {query_opt, institucion}

        Grafo->>Grafo: ROUTE → recuperador_chroma

        Grafo->>ChromaDB: search(query, filtro)
        ChromaDB-->>Grafo: [doc1, doc2, doc3]

        Grafo->>Grafo: ROUTE → sintesis_jasper

        Grafo->>Groq: generate(msg, docs, hist) [temp=0.7]
        Groq-->>Grafo: respuesta_final

    else intencion = GUIA
        Grafo->>Grafo: ROUTE → agente_guia

        Grafo->>Groq: chat(msg, hist) [temp=0.7]
        Groq-->>Grafo: respuesta_simple

    else intencion = FUERA_DOMINIO
        Grafo->>Grafo: ROUTE → fuera_dominio
        Grafo-->>Grafo: respuesta_hardcoded
    end

    Grafo->>Grafo: UPDATE state {respuesta}
    Grafo->>Grafo: UPDATE state {historial}

    Grafo->>MongoDB: Save checkpointer (thread_id)
    MongoDB-->>Grafo: OK

    Grafo-->>Control: resultado

    Control-->>FastAPI: respuesta

    FastAPI-->>User: {respuesta, session_id}
```

---

## 5. MAPA DE RESPONSABILIDADES

```mermaid
mindmap
  root((Sistema Multiagente<br/>Visor 360))
    Clasificación
      nodo_clasificador
        Groq temp=0
        Categorizar mensajes
        Fallback GUIA
      enrutador_de_intencion
        Lógica pura
        Branching decisión
        No IO
    Rama GUÍA
      nodo_guia
        Conversación casual
        Groq temp=0.7
        Max 30 palabras
        Sin markdown
        Fallback RateLimitError
    Rama INFO (RAG)
      nodo_analista_ipn
        Query expansion
        Groq JSON mode
        Extrae institución
        Enum validation
        Fallback original msg
      nodo_recuperador_chroma
        Búsqueda vectorial
        asyncio.to_thread
        Filtro institución
        n_results=3
        Fallback no encontrado
      nodo_sintesis_jasper
        Contexto RAG
        Groq temp=0.7
        Respuesta final
        Actualizar historial
        Fallback genérico
    Rama FUERA
      nodo_fuera_dominio
        Rechazo rápido
        Hardcoded
        Sin Groq
        Zero latency
    Memoria
      MongoDB
        TTL automático
        Checkpointer state
        sesiones_chat
      short_term
        Historial máx 10
        agregar_mensaje
        obtener_historial
        limpiar_sesion
    Base Conocimiento
      ChromaDB
        Embeddings local
        SentenceTransformer
        ipn_knowledge
        Filtro institución
    Config & Utils
      SharedResources
        Singleton Groq
        AsyncGroq client
      utils.py
        llamar_llm_con_reintentos
        @retry decorator
        JSON/texto mode
      config.py
        Settings env
        DATABASE_NAME
    Infraestructura
      database.py
        connect_to_mongo
        close_mongo
        get_db
      checkpointer.py
        MongoDBSaver
        State persistence
        thread_id keys
```

---

## 6. TABLA DE FLUJOS

```
╔════════════════╦════════════════════╦════════════════════╦═══════════╦════════════╗
║ CAMINO         ║ NODOS              ║ LLAMADAS GROQ      ║ TIEMPO    ║ COSTO      ║
╠════════════════╬════════════════════╬════════════════════╬═══════════╬════════════╣
║ GUÍA           ║ Clasificador       ║ 2 calls            ║ ~800ms    ║ ~81 tokens ║
║ (simple)       ║ + Guía             ║ (temp=0.0, 0.7)    ║ (p50)     ║            ║
║                ║                    ║                    ║           ║            ║
║ FUERA_DOMINIO  ║ Clasificador       ║ 1 call             ║ ~200ms    ║ ~1 token   ║
║ (rápido)       ║ + Fuera            ║ (temp=0.0)         ║ (p50)     ║            ║
║                ║                    ║                    ║           ║            ║
║ INFO (RAG)     ║ Clasificador       ║ 4 calls            ║ ~1500ms   ║ ~191 tokens║
║ (completo)     ║ + Analista         ║ (0.0, 0.0 JSON,    ║ (p50)     ║            ║
║                ║ + Recuperador      ║ 0.0, 0.7)          ║           ║            ║
║                ║ + Síntesis         ║ + ChromaDB         ║           ║            ║
╠════════════════╬════════════════════╬════════════════════╬═══════════╬════════════╣
║ PROMEDIO       ║ Máximo 6 nodos     ║ 1-4 calls/request  ║ <2s       ║ ~150 tokens║
║ (SLA)          ║ Estado compartido   ║ MongoDB 2 ops      ║ target    ║ per req    ║
╚════════════════╩════════════════════╩════════════════════╩═══════════╩════════════╝
```

---

## 7. MATRIZ DE ACOPLAMIENTOS

```mermaid
graph TB
    subgraph "ACOPLAMIENTO VERTICAL (Estado)"
        SV1["AgentState"]
        SV2["Todos leen"]
        SV3["Todos escriben"]
        SV1 --> SV2
        SV1 --> SV3
    end

    subgraph "ACOPLAMIENTO HORIZONTAL (Groq)"
        SH1["Groq API"]
        SH2["Clasificador"]
        SH3["Guía"]
        SH4["Analista"]
        SH5["Síntesis"]
        SH1 -.-> SH2
        SH1 -.-> SH3
        SH1 -.-> SH4
        SH1 -.-> SH5
    end

    subgraph "ACOPLAMIENTO TEMPORAL"
        ST1["procesar_mensaje<br/>Orden ejecución"]
        ST2["MongoDB TTL"]
        ST3["Checkpointer"]
        ST4["Historial"]
        ST1 --> ST2
        ST1 --> ST3
        ST1 --> ST4
    end

    subgraph "ACOPLAMIENTO CONCEPTUAL"
        SC1["nodo_sintesis"]
        SC2["Múltiples roles"]
        SC3["RAG + Format<br/>+ Roleplay<br/>+ Historial"]
        SC1 --> SC2
        SC2 --> SC3
    end

    subgraph "ACOPLAMIENTO IMPLÍCITO"
        SI1["Constantes"]
        SI2["Valores hardcodeados<br/>Scattered"]
        SI3["MAX_MENSAJES=10<br/>n_results=3<br/>max_tokens=400"]
        SI1 --> SI2
        SI2 --> SI3
    end

    SV3 -.->|"impacta"| SH2
    SH1 -.->|"impacta"| ST1
    ST1 -.->|"impacta"| SC1
    SC3 -.->|"dispone"| SI3

    style SV1 fill:#ff6b6b,stroke:#000,stroke-width:2px
    style SH1 fill:#ff6b6b,stroke:#000,stroke-width:2px
    style ST1 fill:#ff8787,stroke:#000,stroke-width:2px
    style SC1 fill:#ffa5a5,stroke:#000,stroke-width:2px
    style SI1 fill:#ffb3b3,stroke:#000,stroke-width:2px
```

---

## 8. CRÍTICO: MATRIZ DE FALLO

```mermaid
graph TB
    subgraph "CRITICIDAD"
        C1["🔴 CRÍTICO<br/>App entera cae"]
        C2["🟠 ALTO<br/>Feature no funciona"]
        C3["🟡 MEDIO<br/>Degradación"]
        C4["🟢 BAJO<br/>UX menor"]
    end

    subgraph "PUNTOS DE FALLO"
        F1["❌ Groq API Down"]
        F2["❌ MongoDB Checkpointer"]
        F3["❌ ChromaDB Index Corrupt"]
        F4["❌ State Inconsistency"]
        F5["❌ Rate Limiting"]
        F6["❌ Network Partition"]
        F7["⚠️ TTL Index Fail"]
        F8["⚠️ Memory Leak"]
    end

    F1 --> C1
    F6 --> C1
    F2 --> C2
    F3 --> C2
    F4 --> C2
    F5 --> C3
    F7 --> C3
    F8 --> C4

    style F1 fill:#ff3333,color:#fff
    style F6 fill:#ff3333,color:#fff
    style F2 fill:#ff6633,color:#fff
    style F3 fill:#ff6633,color:#fff
    style F4 fill:#ff6633,color:#fff
    style F5 fill:#ffaa33,color:#000
    style F7 fill:#ffaa33,color:#000
    style F8 fill:#aadd33,color:#000
    style C1 fill:#ff3333,color:#fff,stroke-width:3px
    style C2 fill:#ff6633,color:#fff,stroke-width:3px
    style C3 fill:#ffaa33,color:#000,stroke-width:2px
    style C4 fill:#aadd33,color:#000
```

---

## 9. MONITOREO RECOMENDADO

```mermaid
graph LR
    subgraph "MÉTRICAS LATENCIA"
        L1["P50 Guía: &lt;600ms"]
        L2["P50 Info: &lt;1500ms"]
        L3["P95 Total: &lt;2000ms"]
        L4["Alerta: &gt;5s"]
    end

    subgraph "MÉTRICAS ERROR"
        E1["Classificador: &lt;1%"]
        E2["Guía: &lt;2%"]
        E3["Info Pipeline: &lt;5%"]
        E4["Groq RateLimit: &lt;1%"]
    end

    subgraph "MÉTRICAS RECURSOS"
        R1["MongoDB size &lt;1GB"]
        R2["ChromaDB indexed docs"]
        R3["Sessions active"]
        R4["Memory consumption"]
    end

    subgraph "MÉTRICAS NEGOCIO"
        B1["Token consumption"]
        B2["Groq quota %"]
        B3["Session reuse %"]
        B4["User satisfaction"]
    end

    L1 -.-> L2
    L2 -.-> L3
    L3 --> L4
    E1 -.-> E2
    E2 -.-> E3
    E3 -.-> E4
```
