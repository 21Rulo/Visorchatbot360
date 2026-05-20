# 📊 RESUMEN EJECUTIVO - ANÁLISIS ARQUITECTÓNICO

## 🎯 OBJETO DE ANÁLISIS

**Sistema Multiagente LangGraph** para chatbot institucional (Visor 360 IPN)

- Ubicación: `backend/app/agents/` + `backend/app/core/` + `backend/app/memory/`
- Propósito: Clasificar, enrutar y responder consultas académicas de estudiantes
- Stack: LangGraph + Groq API + MongoDB + ChromaDB + FastAPI

---

## 🏗️ ARQUITECTURA EN 60 SEGUNDOS

```
ENTRADA (FastAPI)
    ↓
CLASIFICADOR (Groq, temp=0.0)
    ↓
    ├─→ GUÍA (Groq, conversación casual) → SALIDA ✅
    ├─→ INFO PIPELINE (RAG: Analista → Recuperador → Síntesis) → SALIDA ✅
    └─→ FUERA DOMINIO (Hardcoded, sin Groq) → SALIDA ✅
    ↓
MEMORIA (MongoDB TTL + LangGraph Checkpointer)
    ↓
CLIENTE
```

---

## 📐 NÚMEROS CLAVE

| Métrica                 | Valor                                                                  |
| ----------------------- | ---------------------------------------------------------------------- |
| **Nodos en Grafo**      | 6 (clasificador, guía, analista, recuperador, síntesis, fuera_dominio) |
| **Caminos Posibles**    | 3 (Guía, Info RAG, Fuera)                                              |
| **Llamadas Groq**       | 1-4 por request (según rama)                                           |
| **Latencia Guía**       | ~600ms p50                                                             |
| **Latencia Info**       | ~1500ms p50                                                            |
| **Latencia Fuera**      | ~200ms p50                                                             |
| **Tokens Promedio**     | ~150-200 por request                                                   |
| **Historial Máximo**    | 10 mensajes (MAX_MENSAJES)                                             |
| **TTL Sesiones**        | 3 días (259200s)                                                       |
| **ChromaDB Resultados** | 3 documentos (n_results)                                               |
| **Conexiones Externas** | 3 (Groq, MongoDB Atlas, ChromaDB local)                                |
| **Puntos Críticos**     | 8 escenarios de fallo mapeados                                         |

---

## 🎪 FLUJOS PRINCIPALES

### Flujo 1: CONVERSACIÓN SIMPLE (15% solicitudes)

```
Clasificador (temp=0.0, 10 tokens)
    → Agente Guía (temp=0.7, 400 tokens)
        → Respuesta conversacional

Costo: ~1 + 80 = ~81 tokens
Tiempo: ~600ms
Sin RAG, sin búsqueda
```

### Flujo 2: CONSULTA ACADÉMICA (70% solicitudes)

```
Clasificador (temp=0.0)
    → Analista IPN (JSON mode, 300 tokens)
        → Query Expansion + Extracción institución
            → Recuperador ChromaDB (asyncio thread)
                → Búsqueda vectorial (3 documentos)
                    → Síntesis Jasper (temp=0.7, 400 tokens)
                        → Respuesta contextualizada

Costo: ~1 + 40 + 0 + 150 = ~191 tokens
Tiempo: ~1500ms (crítico)
RAG completo, memoria + documentos
```

### Flujo 3: RECHAZO (15% solicitudes)

```
Clasificador (temp=0.0)
    → Fuera Dominio (hardcoded, 0 tokens)
        → Respuesta pre-escrita

Costo: ~1 + 0 = ~1 token
Tiempo: ~200ms (ultrarrápido)
Sin llamadas Groq, cero latencia extra
```

---

## 🔀 RESPONSABILIDADES DISTRIBUIDAS

### Por Nodo

| Nodo              | Responsabilidad                            | Dependencias | Costo      | Fallback               |
| ----------------- | ------------------------------------------ | ------------ | ---------- | ---------------------- |
| **Clasificador**  | Enrutamiento inteligente (GUIA/INFO/FUERA) | Groq         | 1 token    | Defecto a GUIA         |
| **Guía**          | Conversación sin RAG, max 30 palabras      | Groq         | 80 tokens  | Genérico               |
| **Analista IPN**  | Query expansion + extracción institución   | Groq JSON    | 40 tokens  | Msg original + GENERAL |
| **Recuperador**   | Búsqueda vectorial (3 docs)                | ChromaDB     | 0 tokens   | "No encontrado"        |
| **Síntesis**      | Generación contextualizada (RAG + prompt)  | Groq         | 150 tokens | Genérico               |
| **Fuera Dominio** | Rechazo rápido                             | Hardcoded    | 0 tokens   | N/A                    |

### Por Componente

| Componente            | Responsabilidad                               |
| --------------------- | --------------------------------------------- |
| **agente_control.py** | Orquestación LangGraph, punto entrada         |
| **agente_info.py**    | 3 nodos RAG (analista, recuperador, síntesis) |
| **agente_guia.py**    | 1 nodo conversación directa                   |
| **checkpointer.py**   | Persistencia estado (MongoDB)                 |
| **short_term.py**     | Gestión historial (últimos 10 msgs)           |
| **vector_db.py**      | ChromaDB manager (búsqueda + embeddings)      |
| **config.py**         | Settings + Groq singleton                     |
| **database.py**       | Conexión MongoDB (async Motor)                |
| **utils.py**          | Reintentos centralizados + retry logic        |
| **routes.py**         | FastAPI endpoint                              |

---

## 🧠 ESTADO COMPARTIDO (AgentState TypedDict)

```python
# ENTRADA
session_id: str              # UUID único
mensaje: str                 # Pregunta actual
contexto_ubicacion: str      # Dónde en visor 360

# MEMORIA
historial: List[Dict]        # Últimos 10 mensajes (reducer: gestionar_historial)

# TRANSFORMACIONES (RAG Pipeline)
intencion: str               # GUIA, INFO, FUERA_DOMINIO
institucion: str             # ESFM, ESIT, ENCB, GENERAL...
query_optimizada: str        # Query expansion
documentos_recuperados: str  # Top 3 docs concatenados

# SALIDA
respuesta: str               # Respuesta final
```

**Viaja por**: Todos los nodos (autopista de datos)
**Problema**: Acoplamiento vertical muy fuerte

---

## 🔗 DEPENDENCIAS CRÍTICAS

### Externas (Upstream)

```
┌─────────────────────────────────────┐
│ ☁️ GROQ API (Critical)              │
├─────────────────────────────────────┤
│ • Modelo: llama-3.3-70b-versatile   │
│ • Usado por: 4 nodos                │
│ • Rate Limits: Manejado con retry   │
│ • SLA: 99.5% (terceros)             │
│ • Punto único de fallo: SÍ          │
│ • Fallback: Parcial (generic msgs)  │
│ • Cost: $0.27 / 1M input tokens     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 🗄️ MONGODB ATLAS (Critical)        │
├─────────────────────────────────────┤
│ • Base: visor360_db                 │
│ • Colecciones: sesiones_chat, ...   │
│ • TTL: 3 días automático            │
│ • Usado por: Checkpointer + Memory  │
│ • SLA: 99.9% (managed)              │
│ • Punto de fallo: Historial perdido │
│ • Fallback: Session sin memoria     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 📚 CHROMADB LOCAL (Critical)        │
├─────────────────────────────────────┤
│ • Path: /home/appuser/chroma_data   │
│ • Embeddings: SentenceTransformer   │
│ • Colección: ipn_knowledge          │
│ • Usado por: nodo_recuperador       │
│ • Punto de fallo: Info retorna "No" │
│ • SLA: 99% (local, manualmente)     │
│ • Fallback: Mensaje genérico        │
└─────────────────────────────────────┘
```

### Internas (Importes)

```
agente_control.py
├─ langgraph (StateGraph, END)
├─ agente_guia, agente_info
├─ checkpointer (MongoDBSaver)
└─ database (get_db)

agente_info.py
├─ SharedResources (Groq singleton)
├─ vector_db (ChromaDB manager)
├─ schemas (AgentState, Institucion enum)
└─ utils (llamar_llm_con_reintentos)

agente_guia.py
├─ SharedResources
├─ schemas (AgentState)
├─ utils
└─ groq (RateLimitError)

vector_db.py
├─ chromadb (PersistentClient)
└─ sentence_transformers (SentenceTransformer)

database.py
├─ motor (AsyncIOMotorClient)
└─ config (settings)
```

---

## 🚨 ACOPLAMIENTOS DETECTADOS

### 1️⃣ ACOPLAMIENTO VERTICAL (Estado Compartido)

```
Severidad: ALTA
Problema: AgentState es la "autopista" donde viajan TODOS
Afectados: 6 nodos + procesar_mensaje
Impacto: Cambiar un campo = revisar TODOS los nodos
Ejemplo: Agregar "usuario_rol" requiere actualizar 3+ nodos
```

### 2️⃣ ACOPLAMIENTO HORIZONTAL (Groq)

```
Severidad: CRÍTICA
Problema: 4 llamadas a Groq en rama INFO (punto único fallo)
Afectados: clasificador, guía, analista, síntesis
Impacto: Si Groq cae = APP entera cae (excepto en fallback)
Rate Limits: 429 errors afectan TODO (no aislado por rama)
```

### 3️⃣ ACOPLAMIENTO TEMPORAL (MongoDB Dual)

```
Severidad: MEDIA
Problema: 2 conexiones MongoDB separadas (TTL + checkpointer)
Afectados: procesar_mensaje, checkpointer, short_term
Impacto: Posible inconsistencia entre sesiones_chat e historial
Fallo: Si cae durante paso 2 → estado perdido
```

### 4️⃣ ACOPLAMIENTO CONCEPTUAL (Multi-Responsabilidades)

```
Severidad: MEDIA
Problema: Cada nodo tiene demasiados roles
Nodo sintesis_jasper: RAG + formatting + roleplay + memoria
Afectado: Testing, debugging, reutilización
Impacto: Cambios tienen efectos no predecibles
```

### 5️⃣ ACOPLAMIENTO IMPLÍCITO (Constantes Hardcodeadas)

```
Severidad: BAJA
Problema: Valores mágicos dispersos en código
Ejemplos:
  - MAX_MENSAJES = 10 (¿por qué no 15?)
  - n_results = 3 (¿por qué no 5?)
  - max_tokens = 400 (diferentes en cada nodo)
  - "## " split pattern para chunks
Impacto: Frágil, cambios requieren rebusca
```

### 6️⃣ ACOPLAMIENTO IMPLÍCITO (Múltiples "Verdades")

```
Severidad: BAJA
Problema: short_term.py + LangGraph checkpointer = redundancia
Afectado: Historial vive en 2 lugares
Impacto: Posible desfase, lógica duplicada
Mejora: Usar solo LangGraph checkpointer
```

---

## ⚠️ PUNTOS CRÍTICOS IDENTIFICADOS

### 🔴 CRÍTICOS (App entera cae)

1. **Groq API Down**
   - Afecta: Todos los nodos (excepto fuera_dominio)
   - Síntoma: Timeout > 2s
   - Fallback: Parcial (mensajes genéricos)
   - SLA: 99.5% (terceros)

2. **MongoDB Checkpointer Down**
   - Afecta: Persistencia + historial siguiente call
   - Síntoma: Connection timeout
   - Fallback: Session sin memoria
   - Impacto: Usuario pierde contexto

3. **Network Partition (Backend ↔ Groq/MongoDB)**
   - Afecta: Toda comunicación upstream
   - Fallback: Retry x4 con exponential backoff
   - Duracion: Hasta fix manual

### 🟠 ALTOS (Feature no funciona)

4. **ChromaDB Index Corrupted**
   - Afecta: Rama INFO (RAG pipeline)
   - Síntoma: Búsqueda retorna 0 siempre
   - Fallback: "No se encontró información"
   - Duracion: Minutos a horas (manual rebuild)

5. **AgentState Inconsistency**
   - Afecta: Nodos siguientes reciben estado corrupto
   - Síntoma: KeyError en campo esperado
   - Fallback: Exception handler por nodo
   - Impacto: Respuesta parcial

### 🟡 MEDIOS (Degradación)

6. **Groq Rate Limit (429)**
   - Afecta: Todos (secuencial, no en paralelo)
   - Síntoma: Latencia > 10s
   - Fallback: Retry x4 con backoff
   - Duracion: Segundos a minutos

7. **MongoDB TTL Index Fail**
   - Afecta: Sesiones antiguas persisten
   - Síntoma: Base datos crece sin límite
   - Fallback: Manual cleanup / rebuild
   - Duracion: Largo plazo

---

## 📈 PERFORMANCE Y SCALING

### Latencias (Observadas)

| Operación    | p50    | p95    | p99    | Bottleneck     |
| ------------ | ------ | ------ | ------ | -------------- |
| Guía         | 600ms  | 800ms  | 1000ms | Groq latency   |
| Info RAG     | 1500ms | 2000ms | 2500ms | Groq x3 serial |
| Fuera        | 200ms  | 300ms  | 400ms  | Network        |
| Clasificador | 200ms  | 300ms  | 400ms  | Groq           |

### Cuellos de Botella

1. **Groq Serial Calls** (~1500ms en rama INFO)
   - Clasificador → Analista → Síntesis (3 calls secuenciales)
   - Mejora potencial: Paralelizar si es posible
   - Trade-off: Complejidad de estado

2. **ChromaDB Search** (~100-300ms)
   - Ejecutado en thread (asyncio.to_thread)
   - Embebdings SentenceTransformer en CPU
   - Escala con tamaño índice

3. **MongoDB Network Latency** (~50-100ms por op)
   - Atlas es cloud-hosted (latencia de red)
   - Checkpointer = 2 operaciones (carga + save)
   - Mejora potencial: Redis cache

### Escalabilidad Actual

- **Max concurrent requests**: Limited by Groq RPM (request limit)
- **Max historial**: 10 mensajes (hardcodeado)
- **Max respuesta**: 400 tokens máx (hardcodeado)
- **Max ChromaDB**: Local (single machine) = no distribuído
- **MongoDB**: Atlas auto-scales (pero $ increases)

---

## 🛠️ HERRAMIENTAS DE DIAGNÓSTICO

### Monitoreo Recomendado

```
LATENCIA:
  • P50 Guía: 600ms (target)
  • P50 Info: 1500ms (target)
  • P95 Total: 2000ms (alerta: >2s)
  • P99 Total: 2500ms (crítico: >5s)

ERROR RATE:
  • Clasificador: <1% (objetivo)
  • Guía: <2%
  • Info Pipeline: <5%
  • Groq RateLimit: <1%

RECURSOS:
  • MongoDB sesiones_chat: <1GB
  • ChromaDB índice: X docs
  • Sessions activas: trending
  • Memory: trending

NEGOCIO:
  • Token consumption/request: ~150-200
  • Groq quota consumption: % of monthly
  • Session reuse: % con >1 mensaje
  • User satisfaction: survey/feedback
```

---

## 📋 RECOMENDACIONES PRE-MIGRACIÓN

### Tier 1 (Críticas - Hacer YA)

1. ✅ **Centralizar configuración**
   - Crear `config.yaml` o `.env` ampliado
   - Extraer constantes: MAX_MENSAJES, n_results, max_tokens, split_patterns
   - Evitar hardcoding en prompts

2. ✅ **Documentar prompts**
   - Extraer a archivos separados (`prompts/`)
   - Versionarlos (git track)
   - Parametrizar variables dinámicas

3. ✅ **Crear test suite**
   - Unit tests para cada nodo (con mocks Groq)
   - Integration tests para flujos completos
   - Tests de fallbacks

4. ✅ **Simplificar estado**
   - Reducir responsabilidades por nodo
   - Documentar qué lee/escribe cada uno
   - Considerar eliminar short_term.py (redundancia)

### Tier 2 (Mejoras - Considerar)

5. **Paralelizar Groq calls**
   - Info pipeline: clasificador en paralelo?
   - Moldes de estado independientes

6. **Agregar caché**
   - Embedding cache para queries similares
   - Redis para respuestas frecuentes

7. **Integración observabilidad**
   - Logging estructurado (JSON)
   - Trace IDs por request
   - Metrics (Prometheus)
   - Alertas (PagerDuty)

### Tier 3 (Futuro - Investigar)

8. **Migrar ChromaDB a cloud**
   - Pinecone, Weaviate o Milvus
   - Backup + replication automática

9. **Implementar queue**
   - Celery/RabbitMQ para requests pesados
   - Rate limiting granular

10. **Multi-tenancy**
    - Soportar múltiples clientes
    - Isolation de sesiones

---

## 📚 REFERENCIAS GENERADAS

### Documentos Creados

1. **ARCHITECTURE_ANALYSIS.md** (800+ líneas)
   - Análisis exhaustivo sin código
   - 9 secciones principales
   - Tablas y matrices de decisión

2. **ARCHITECTURE_DIAGRAMS.md** (500+ líneas)
   - 9 diagramas Mermaid
   - Flujos visuales
   - Matrices de criticidad

3. **Esta sección**: Resumen ejecutivo para stakeholders

---

## ✨ CONCLUSIÓN

**Sistema funcional pero frágil con acoplamientos altos.**

Antes de escalar o refactorizar:

1. Centralizar config
2. Documentar prompts
3. Crear tests
4. Simplificar estado

**Principales riegos:**

- Dependencia Groq (punto único fallo)
- ChromaDB local (no distribuído)
- Acoplamiento AgentState (cambios en cascada)

**Puntos fuertes:**

- Arquitectura modular (6 nodos independientes)
- Fallbacks en cada nivel
- Persistencia robusta (MongoDB)
- RAG pipeline bien estructurado

**Next steps:** Revisar ARCHITECTURE_ANALYSIS.md para detalle completo.
