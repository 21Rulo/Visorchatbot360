import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

function gradosACoordenadas(pitch, yaw, radio) {
    const phi = pitch * (Math.PI / 180);
    const theta = yaw * (Math.PI / 180);

    const x = radio * Math.cos(phi) * Math.sin(theta);
    const y = radio * Math.sin(phi);
    const z = -radio * Math.cos(phi) * Math.cos(theta);

    return new THREE.Vector3(x, y, z);
}

export function iniciarVisor(mapa) {
    const escena = new THREE.Scene();
    const camara = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camara.position.set(0, 0, 0.1);

    const renderizador = new THREE.WebGLRenderer({ antialias: true });
    renderizador.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderizador.domElement);

    const controles = new OrbitControls(camara, renderizador.domElement);
    controles.enableZoom = false;
    controles.enablePan = false;

    const geometria = new THREE.SphereGeometry(500, 60, 40);
    geometria.scale(-1, 1, 1);
    const cargadorTextura = new THREE.TextureLoader();
    const mapaIcono = cargadorTextura.load('/assets/arrow1.png',() => console.log("✅ Textura de flecha cargada correctamente"),
    undefined,
    (err) => console.error("❌ Error cargando la flecha:", err));
    mapaIcono.colorSpace = THREE.SRGBColorSpace;

    const tituloUI = document.getElementById('titulo-ubicacion');
    const tooltipUI = document.getElementById('tooltip-hotspot');
    const material = new THREE.MeshBasicMaterial();
    const esfera = new THREE.Mesh(geometria, material);
    escena.add(esfera);

    const grupoHotspots = new THREE.Group();
    escena.add(grupoHotspots);

    let fovObjetivo = 75;

    // --- RAYCASTER ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    // --- HOVER ---
    window.addEventListener('mousemove', (event) => {
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, camara);

        const intersecciones = raycaster.intersectObjects(grupoHotspots.children);
        
        if (intersecciones.length > 0) {
            const objeto = intersecciones[0].object;
            objeto.userData.escalaObjetivo = 80;
            document.body.style.cursor = 'pointer';
            
            tooltipUI.innerText = objeto.userData.texto;
            tooltipUI.style.left = `${event.clientX + 15}px`;
            tooltipUI.style.top = `${event.clientY + 15}px`;
            tooltipUI.classList.remove('oculto');
            
        } else {
            document.body.style.cursor = 'default';
            tooltipUI.classList.add('oculto');
            
            grupoHotspots.children.forEach(hs => hs.userData.escalaObjetivo = 35);
        }
    });

    window.addEventListener('click', (event) => {
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, camara);

        const intersecciones = raycaster.intersectObjects(grupoHotspots.children);
        if (intersecciones.length > 0) {
            const hotspotTocado = intersecciones[0].object;
            const idDestino = hotspotTocado.userData.destino;
            const yawLlegada = hotspotTocado.userData.yaw_llegada ?? 0;
            cargarNodo(idDestino, yawLlegada);
            return;
        }

        if (event.ctrlKey) {
            const interseccionEsfera = raycaster.intersectObject(esfera);
            if (interseccionEsfera.length > 0) {
                const punto = interseccionEsfera[0].point;
                const radioV = punto.length();
                const pitch = Math.asin(punto.y / radioV) * (180 / Math.PI);
                const yaw = Math.atan2(punto.x, -punto.z) * (180 / Math.PI);

                console.log("%c📍 Coordenadas capturadas:", "color: #00ff00; font-weight: bold; font-size: 14px;");
                console.log(`
        {
          "destino": "ID_DEL_DESTINO",
          "texto": "Ir a...",
          "pitch": ${pitch.toFixed(2)},
          "yaw": ${yaw.toFixed(2)}
        }`);
                alert(`Coordenadas: Pitch ${pitch.toFixed(2)}, Yaw ${yaw.toFixed(2)}`);
            }
        }
    });

    // --- FUNCIÓN PARA CARGAR UN NODO ---
    // Cambiamos el valor por defecto a null para saber si venimos de un clic o del inicio
    function cargarNodo(idNodo, yawLlegada = null) {
        const nodoData = mapa.nodos[idNodo];
        if (!nodoData) return;
        tituloUI.innerText = nodoData.titulo;

        // LÓGICA DE GIRO: Si hay yawLlegada (clic), lo usamos. Si es null (inicio), usamos el yaw_inicio del JSON (o 0 si no existe).
        const anguloGiro = yawLlegada !== null ? yawLlegada : (nodoData.yaw_inicio || 0);

        const telon = document.getElementById('cortinilla-transicion');
        telon.style.opacity = '1';

        setTimeout(() => {
            cargadorTextura.load(nodoData.imagen_url, (textura) => {
                if (esfera.material.map) {
                    esfera.material.map.dispose(); 
                }
                textura.colorSpace = THREE.SRGBColorSpace;
                esfera.material.map = textura;
                esfera.material.needsUpdate = true;

                // PASO 1: Resetear rotaciones a cero
                esfera.rotation.y = 0;
                grupoHotspots.rotation.y = 0;

                // PASO 2: Limpiar hotspots anteriores y agregar los nuevos
                grupoHotspots.clear();

                nodoData.hotspots.forEach(hs => {
                    const materialSprite = new THREE.SpriteMaterial({ 
                        map: mapaIcono,
                        color: 0xffffff,       
                        transparent: true,     
                        alphaTest: 0.1,        
                        depthTest: false,
                        depthWrite: false
                    });
                    const sprite = new THREE.Sprite(materialSprite);
                    
                    sprite.scale.set(35, 35, 1);

                    const posicion = gradosACoordenadas(hs.pitch, hs.yaw, 450);
                    sprite.position.copy(posicion);
                    
                    sprite.userData = {
                        destino: hs.destino,
                        yaw_llegada: hs.yaw_llegada,
                        texto: hs.texto,
                        escalaObjetivo:35
                    };

                    grupoHotspots.add(sprite);
                });

                // PASO 3: Aplicar la rotación a esfera + hotspots juntos usando nuestra nueva variable
                const rotacionRadianes = anguloGiro * (Math.PI / 180);
                esfera.rotation.y = -rotacionRadianes;
                grupoHotspots.rotation.y = -rotacionRadianes;

                // PASO 4: Resetear la cámara para que mire al frente al entrar
                controles.reset();

                telon.style.opacity = '0';
            });
        }, 200);
    }

    cargarNodo(mapa.nodo_inicial);

    function animar() {
        requestAnimationFrame(animar);
        controles.update();
        const tiempo = Date.now() * 0.002;

        grupoHotspots.children.forEach(hs => {
            // 1. Suavizado (Lerp): 0.1 es la velocidad de la elasticidad
            const escalaActual = hs.scale.x;
            const escalaDestino = hs.userData.escalaObjetivo;
            let nuevaEscala = escalaActual + (escalaDestino - escalaActual) * 0.1;

            // 2. Pulso: Solo se aplica si NO estamos en hover (escala objetivo es 35)
            // Opcional: puedes aplicarlo siempre para un efecto más vivo
            if (escalaDestino === 35) {
                const pulso = Math.sin(tiempo) * 2; // Oscilación de +/- 2 unidades
                nuevaEscala += pulso;
            }

            hs.scale.set(nuevaEscala, nuevaEscala, 1);
        });

        // --- ZOOM SUAVE (via FOV) ---
        if (Math.abs(camara.fov - fovObjetivo) > 0.1) {
            camara.fov += (fovObjetivo - camara.fov) * 0.1;
            camara.updateProjectionMatrix();
        }

        // --- BRÚJULA ---
        const anguloRadianes = controles.getAzimuthalAngle();
        const grados = anguloRadianes * (180 / Math.PI);
        const brujulaHTML = document.getElementById('icono-brujula');
        if (brujulaHTML) {
            brujulaHTML.style.transform = `rotate(${-grados}deg)`;
        }

        renderizador.render(escena, camara);
    }
    animar();

    window.addEventListener('resize', () => {
        camara.aspect = window.innerWidth / window.innerHeight;
        camara.updateProjectionMatrix();
        renderizador.setSize(window.innerWidth, window.innerHeight);
    });

    // --- ZOOM (via FOV) ---
    function hacerZoom(cantidad) {
        const ajuste = cantidad < 0 ? -5 : 5;
        fovObjetivo += ajuste;
        fovObjetivo = THREE.MathUtils.clamp(fovObjetivo, 30, 90);
    }

    return { cargarNodo, hacerZoom };
}