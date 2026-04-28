# 🐳 Guía de Docker + Rocky Linux + Nginx

## PARTE 1: Ejecutar con Docker Compose (Local)

### Requisitos previos

```bash
# Verificar que tienes Docker y Docker Compose instalados
docker --version
docker-compose --version
```

### Pasos para ejecutar localmente

#### 1. Preparar variables de entorno

```bash
cd infra/

# Crear archivo .env basado en el ejemplo
cp .env.prod .env

# Editar y agregar tu GROQ_API_KEY
# nano .env  (o usa tu editor favorito)
```

#### 2. Construir y ejecutar los contenedores

```bash
# Estar en la carpeta infra/
docker-compose up --build
```

**Salida esperada:**

```
visor360-backend  | INFO:     Uvicorn running on http://0.0.0.0:8000
visor360-frontend | 2026/04/28 12:00:00 [notice] master process started
```

#### 3. Verificar que funciona

```bash
# En otra terminal

# Backend
curl http://localhost:8000/
# Respuesta: {"mensaje":"Servidor activo"}

# Frontend
curl http://localhost:3000/
# Respuesta: index.html
```

#### 4. Detener los contenedores

```bash
docker-compose down
```

---

## PARTE 2: Desplegar en Rocky Linux + Nginx

### Fase 1: Preparación del Servidor Rocky Linux

#### 1. Conectarse al servidor

```bash
ssh root@tu_ip_servidor
```

#### 2. Instalar Docker y Docker Compose

```bash
# Actualizar sistema
dnf update -y
dnf install -y dnf-plugins-core

# Instalar Docker
dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Iniciar Docker
systemctl start docker
systemctl enable docker

# Agregar usuario al grupo docker (opcional, para ejecutar sin sudo)
usermod -aG docker $USER
newgrp docker
```

#### 3. Crear directorio de la aplicación

```bash
mkdir -p /opt/visor360
cd /opt/visor360
```

#### 4. Clonar o copiar el proyecto

```bash
# Opción A: Clonar desde Git
git clone https://tu_repo.git .

# Opción B: Copiar archivos (desde tu máquina local)
# En tu PC:
scp -r c:/Users/rulom/OneDrive/Documentos/SIIS/visor-360-institucional/* root@tu_ip:/opt/visor360/
```

#### 5. Configurar variables de entorno

```bash
cd /opt/visor360/infra

# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tu GROQ_API_KEY
nano .env
```

---

### Fase 2: Ejecutar con Docker Compose

#### 1. Construir y ejecutar (primera vez)

```bash
cd /opt/visor360
docker-compose -f infra/docker-compose.yml up -d --build
```

#### 2. Verificar estado

```bash
docker-compose -f infra/docker-compose.yml ps

# Debería mostrar:
# NAME                 COMMAND       STATUS
# visor360-backend     uvicorn ...   Up (healthy)
# visor360-frontend    nginx ...     Up (healthy)
```

#### 3. Ver logs

```bash
# Todos los contenedores
docker-compose -f infra/docker-compose.yml logs -f

# Solo backend
docker-compose -f infra/docker-compose.yml logs -f backend

# Solo frontend
docker-compose -f infra/docker-compose.yml logs -f frontend
```

---

### Fase 3: Nginx como Reverse Proxy (RECOMENDADO)

#### ¿Por qué Nginx como reverse proxy?

- Los contenedores corren en puertos privados (8000, 3000)
- Nginx expone un único puerto (80/443)
- Mejor rendimiento y seguridad
- Gestión de SSL/HTTPS fácil

#### 1. Instalar Nginx en el host

```bash
dnf install -y nginx

# Iniciar y habilitar
systemctl start nginx
systemctl enable nginx
```

#### 2. Crear configuración de Nginx

```bash
# Crear archivo de configuración
nano /etc/nginx/conf.d/visor360.conf
```

**Contenido del archivo:**

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name tu_dominio.com www.tu_dominio.com;

    # Redirigir HTTP a HTTPS (opcional, si tienes certificado)
    # return 301 https://$server_name$request_uri;

    # Raíz del sitio (frontend)
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API backend
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

#### 3. Validar y recargar Nginx

```bash
# Validar sintaxis
nginx -t

# Recargar configuración
systemctl reload nginx
```

#### 4. Permitir puertos en el firewall

```bash
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

---

### Fase 4: Agregar HTTPS con Certbot (OPCIONAL pero RECOMENDADO)

```bash
# Instalar Certbot
dnf install -y certbot python3-certbot-nginx

# Obtener certificado
certbot --nginx -d tu_dominio.com -d www.tu_dominio.com

# Certbot automáticamente actualiza nginx.conf
# Verificar renovación automática
systemctl enable certbot-renew.timer
```

---

## Estructura Final en Rocky Linux

```
/opt/visor360/
├── backend/
├── frontend/
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile_Back
│   ├── Dockerfile_Front
│   ├── nginx.conf (para Nginx en contenedores)
│   └── .env
├── .git/
└── docker-compose.yml (si está en root)

/etc/nginx/conf.d/
└── visor360.conf  (reverse proxy del host)
```

---

## Comandos Útiles en Rocky Linux

```bash
# Ver estado de Docker
docker ps
docker stats

# Limpiar espacios de almacenamiento
docker system prune -a

# Actualizar contenedores
cd /opt/visor360
git pull
docker-compose -f infra/docker-compose.yml up -d --build

# Reiniciar servicios
systemctl restart nginx
docker-compose -f infra/docker-compose.yml restart

# Ver logs en tiempo real
docker-compose -f infra/docker-compose.yml logs -f --tail 100
```

---

## Diagrama de Flujo

```
CLIENTE (Internet)
    ↓
   [Nginx en host Rocky Linux]  (80/443)
    ↓
[Frontend Container]  ← proxy_pass → 3000
    ├── /index.html
    ├── /js/
    └── /api/* → [Backend Container]  ← proxy_pass → 8000
         ├── /api/chat
         └── Conexión a Groq API
```

---

## Checklist Deployment

- [ ] Docker y Docker Compose instalados en Rocky Linux
- [ ] Código clonado o copiado en `/opt/visor360`
- [ ] Variables de entorno configuradas (GROQ_API_KEY)
- [ ] Contenedores ejecutándose sin errores
- [ ] Nginx instalado en el host
- [ ] Configuración de Nginx validada
- [ ] Firewall abierto para HTTP/HTTPS
- [ ] Certificado SSL instalado (Certbot)
- [ ] DNS apuntando a la IP del servidor
- [ ] Prueba de acceso funcionando

---

## Troubleshooting

### Los contenedores no inician

```bash
# Ver logs
docker-compose -f infra/docker-compose.yml logs backend
docker-compose -f infra/docker-compose.yml logs frontend

# Problema común: puerto ocupado
lsof -i :8000
lsof -i :3000
```

### Nginx no conecta a los contenedores

```bash
# Verificar si los contenedores están en la red correcta
docker network ls
docker network inspect visor360-network

# Los servicios deben poder resolverse por nombre (backend:8000, frontend:3000)
```

### CORS errors

```bash
# Backend ya tiene CORS habilitado en main.py
# Si hay problemas, agregar headers en nginx.conf:
add_header 'Access-Control-Allow-Origin' '*' always;
```
