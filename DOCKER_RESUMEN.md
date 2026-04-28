# 🚀 RESUMEN: Docker + Rocky Linux + Nginx

## ✅ Lo que creé para ti

### 1. **Dockerfile_Back** (Backend con FastAPI)

```dockerfile
✓ Multi-stage build (más ligero)
✓ Usuario no-root (seguridad)
✓ Health checks automáticos
✓ Uvicorn en puerto 8000
```

### 2. **Dockerfile_Front** (Frontend con Vite + Nginx)

```dockerfile
✓ Build de Vite en Node 20
✓ Servido por Nginx
✓ SPA routing automático
✓ Proxy a API backend
✓ Compresión Gzip
✓ Cache headers para assets
```

### 3. **docker-compose.yml**

```yaml
✓ Dos servicios (backend + frontend)
✓ Red interna: visor360-network
✓ Health checks
✓ Dependencias configuradas
✓ Variables de entorno
```

### 4. **nginx.conf**

```nginx
✓ Proxy inverso hacia backend
✓ SPA routing (/api/* redirige a backend)
✓ Caché de assets estáticos (30 días)
✓ Compresión Gzip
✓ Headers de seguridad
```

### 5. **DOCKER_DEPLOYMENT.md**

```markdown
✓ Guía completa de instalación local
✓ Pasos para Rocky Linux
✓ Configuración de Nginx en el host
✓ Certificados SSL con Certbot
✓ Troubleshooting
✓ 200+ líneas de instrucciones
```

### 6. **docker.sh**

```bash
✓ Script helper para comandos comunes
✓ Colores y output amigable
✓ 15+ comandos disponibles
```

---

## 📊 Arquitectura

```
                        CLIENTE (Internet)
                              ↓
                              [Router/Firewall]
                              ↓
                 ┌────────────────────────┐
                 │  ROCKY LINUX SERVER    │
                 │   (192.168.x.x)        │
                 ├────────────────────────┤
                 │                        │
                 │  ┌──────────────────┐  │
                 │  │  Nginx (Host)    │  │  ← Puerto 80/443 (público)
                 │  │  Reverse Proxy   │  │
                 │  └──────────────────┘  │
                 │     ↓           ↓      │
              ┌──────────────────────────┐│
              │  Docker Network          ││
              │  (visor360-network)      ││
              │                          ││
              │  ┌──────────────────┐   ││
              │  │ Backend:8000     │   ││
              │  │ FastAPI+Uvicorn  │   ││
              │  │ - Groq API conn  │   ││
              │  │ - Chat endpoint  │   ││
              │  └──────────────────┘   ││
              │                          ││
              │  ┌──────────────────┐   ││
              │  │ Frontend:3000    │   ││
              │  │ Nginx+Vite Build │   ││
              │  │ - Three.js scene │   ││
              │  │ - Chat UI        │   ││
              │  └──────────────────┘   ││
              │                          ││
              └──────────────────────────┘│
                 │                        │
                 │ Puertos:               │
                 │ ├─ 80 (HTTP)           │
                 │ ├─ 443 (HTTPS)         │
                 │ └─ 22 (SSH admin)      │
                 └────────────────────────┘
                              ↓
                    [Groq/OpenAI API]
```

---

## 🚀 Flujo de Inicio Rápido

### Local (Desarrollo)

```bash
# 1. Preparar
cp infra/.env.prod infra/.env
# Editar infra/.env con GROQ_API_KEY

# 2. Ejecutar
./docker.sh up

# 3. Acceder
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000

# 4. Ver logs
./docker.sh logs backend

# 5. Detener
./docker.sh down
```

### Rocky Linux (Producción)

```bash
# 1. Conectar al servidor
ssh root@tu_ip

# 2. Instalar Docker
dnf install -y docker-ce docker-compose-plugin

# 3. Clonar proyecto
git clone https://tu_repo /opt/visor360

# 4. Configurar
cd /opt/visor360
cp infra/.env.prod infra/.env
nano infra/.env  # Editar GROQ_API_KEY

# 5. Ejecutar
docker-compose -f infra/docker-compose.yml up -d

# 6. Instalar Nginx host
dnf install -y nginx
nano /etc/nginx/conf.d/visor360.conf
systemctl reload nginx

# 7. Agregar SSL (Certbot)
dnf install -y certbot python3-certbot-nginx
certbot --nginx -d tu_dominio.com
```

---

## 🎯 Ventajas de esta Configuración

| Aspecto              | Beneficio                              |
| -------------------- | -------------------------------------- |
| **Aislamiento**      | Cada servicio en su contenedor         |
| **Escalabilidad**    | Fácil agregar más replicas             |
| **Portabilidad**     | Funciona en cualquier máquina          |
| **Reproducibilidad** | Mismo comportamiento siempre           |
| **Seguridad**        | Usuarios no-root, sin puertos privados |
| **Mantenimiento**    | Actualizaciones sin downtime           |

---

## 📝 Archivos Creados

```
infra/
├── Dockerfile_Back        ← Backend FastAPI
├── Dockerfile_Front       ← Frontend Nginx+Vite
├── docker-compose.yml     ← Orquestación
├── nginx.conf             ← Config interna
└── .env.example           ← Template variables

DOCKER_DEPLOYMENT.md       ← Guía completa (200+ líneas)
docker.sh                  ← Script helper
.gitignore                 ← Actualizado
```

---

## 🔐 Seguridad

```
✓ Usuarios no-root en contenedores
✓ Claves API en variables de entorno (.env)
✓ Nginx como reverse proxy (puertos privados ocultos)
✓ Health checks automáticos
✓ Headers de seguridad en Nginx
✓ CORS habilitado en FastAPI
✓ Certificados SSL (Certbot)
```

---

## 📊 Recursos

| Recurso        | Típico   | Producción |
| -------------- | -------- | ---------- |
| CPU Backend    | 0.5 vCPU | 2+ vCPU    |
| RAM Backend    | 512 MB   | 2+ GB      |
| CPU Frontend   | 0.2 vCPU | 0.5+ vCPU  |
| RAM Frontend   | 256 MB   | 512+ MB    |
| Almacenamiento | 2 GB     | 10+ GB     |

---

## 🆘 Próximos Pasos

1. **Editar infra/.env** con tu GROQ_API_KEY
2. **Ejecutar localmente**: `./docker.sh up`
3. **Verificar**: http://localhost:3000
4. **Leer**: DOCKER_DEPLOYMENT.md (instrucciones completas)
5. **Desplegar**: Seguir la sección "Rocky Linux" del documento

---

## 💡 Comandos Más Usados

```bash
# Ver estado
docker-compose -f infra/docker-compose.yml ps

# Logs en vivo
docker-compose -f infra/docker-compose.yml logs -f

# Entrar a contenedor
docker-compose -f infra/docker-compose.yml exec backend bash

# Reiniciar
docker-compose -f infra/docker-compose.yml restart

# Parar todo
docker-compose -f infra/docker-compose.yml down

# O usar el script
./docker.sh up
./docker.sh logs backend
./docker.sh bash-backend
```

---

## 📞 Notas Importantes

1. **GROQ_API_KEY**: Configúrala en `infra/.env` antes de ejecutar
2. **Firewall Rocky**: Abre puertos 80, 443, 22 con `firewall-cmd`
3. **DNS**: Apunta tu dominio a la IP del servidor
4. **Certificado SSL**: Usa Certbot para HTTPS automático
5. **Logs**: Los puedes ver con `docker-compose logs -f`

---

¿Tienes dudas sobre algún paso? Revisa **DOCKER_DEPLOYMENT.md** para más detalles.
