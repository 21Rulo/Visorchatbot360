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

// --- CREACIÓN DEL OVERLAY DE AYUDA AL INICIO ---
function crearOverlayAyuda() {
    const overlay = document.createElement('div');
    overlay.id = 'overlay-ayuda';
    // Estilos inline básicos, la animación va en CSS
    overlay.style.cssText = `
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(0, 0, 0, 0.4);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 100;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.5s ease-in-out;
    `;

    // Icono SVG animado (sirve para PC y móvil visualmente)
    overlay.innerHTML = `
    <div class="animacion-arrastre">
        <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 8l-4 4 4 4"></path>
            <path d="M16 8l4 4-4 4"></path>
            <path d="M4 12h16"></path>
        </svg>
    </div>
    <p style="color: white; font-family: sans-serif; margin-top: 15px; text-align: center; text-shadow: 1px 1px 3px black;">
        ${window.innerWidth > 1024 ? 'Haz clic y arrastra para mirar' : 'Desliza para explorar'}
    </p>
    `;

    document.body.appendChild(overlay);
    return overlay;
}


export function iniciarVisor(mapa, onNodeChange) {
    const escena = new THREE.Scene();
    const camara = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camara.position.set(0, 0, 0.1);

    const renderizador = new THREE.WebGLRenderer({ antialias: false });
    renderizador.setPixelRatio(Math.min(window.devicePixelRatio, 2)); 
    renderizador.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderizador.domElement);
    const canvas = renderizador.domElement;
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.zIndex = '0'; 

    const controles = new OrbitControls(camara, renderizador.domElement);
    controles.enableZoom = false;
    controles.enablePan = false;
    controles.rotateSpeed = 0.4;
    controles.enableDamping = true;
    controles.dampingFactor = 0.05;

    const geometria = new THREE.SphereGeometry(500, 32, 32);
    geometria.scale(-1, 1, 1);
    const cargadorTextura = new THREE.TextureLoader();
    const mapaIcono = cargadorTextura.load('/visor_v2/assets/src/arrow1.png',
        () => console.log("✅ Textura de flecha cargada correctamente"),
        undefined,
        (err) => console.error("❌ Error cargando la flecha:", err)
    );
    mapaIcono.colorSpace = THREE.SRGBColorSpace;

    const tituloUI = document.getElementById('titulo-ubicacion');
    const tooltipUI = document.getElementById('tooltip-hotspot');
    const material = new THREE.MeshBasicMaterial();
    const esfera = new THREE.Mesh(geometria, material);
    escena.add(esfera);

    const grupoHotspots = new THREE.Group();
    escena.add(grupoHotspots);

    let fovObjetivo = 75;
    let posicionObjetivoCamara = new THREE.Vector3(0, 0, 0.1);
    let ultimoHotspotTocado = null;
    let esPrimerNodo = true;
    let animandoPlaneta = false;
    
    // --- LÓGICA DE INACTIVIDAD ---
    const overlayAyuda = crearOverlayAyuda();
    let temporizadorInactividad;
    const TIEMPO_INACTIVIDAD = 30000; // 30 segundos

    function resetearInactividad() {
        // Ocultar el overlay si estaba visible
        if (overlayAyuda.style.opacity === '1') {
            overlayAyuda.style.opacity = '0';
            overlayAyuda.style.pointerEvents = 'none';
        }

        // Limpiar el temporizador anterior
        clearTimeout(temporizadorInactividad);

        // Iniciar un nuevo temporizador
        temporizadorInactividad = setTimeout(() => {
            overlayAyuda.style.opacity = '1';
            // Permitir clics a través del overlay para que al tocar desaparezca inmediatamente
            overlayAyuda.style.pointerEvents = 'none'; 
        }, TIEMPO_INACTIVIDAD);
    }

    // --- RAYCASTER ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseMove = (event) => {
        resetearInactividad(); // Reset al mover ratón
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
    };

    const onClick = (event) => {
        resetearInactividad(); // Reset al hacer clic
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, camara);

        const intersecciones = raycaster.intersectObjects(grupoHotspots.children);
        
        if (intersecciones.length > 0) {
            const hotspotTocado = intersecciones[0].object;
            const idDestino = hotspotTocado.userData.destino;
            const yawLlegada = hotspotTocado.userData.yaw_llegada ?? 0;

            // --- LÓGICA PARA MÓVILES ---
            if (ultimoHotspotTocado === hotspotTocado || window.innerWidth > 1024) {
                tooltipUI.classList.add('oculto');
                cargarNodo(idDestino, yawLlegada);
                ultimoHotspotTocado = null;
            } else {
                ultimoHotspotTocado = hotspotTocado;
                tooltipUI.innerText = hotspotTocado.userData.texto;
                tooltipUI.style.left = `${event.clientX}px`;
                tooltipUI.style.top = `${event.clientY - 40}px`;
                tooltipUI.classList.remove('oculto');
                
                setTimeout(() => {
                    if (ultimoHotspotTocado === hotspotTocado) ultimoHotspotTocado = null;
                }, 3000);
            }
            return;
        }
        tooltipUI.classList.add('oculto');
        ultimoHotspotTocado = null;
    };

    const onResize = () => {
        camara.aspect = window.innerWidth / window.innerHeight;
        camara.updateProjectionMatrix();
        renderizador.setSize(window.innerWidth, window.innerHeight);
        
        // Actualizar texto del overlay si cambia de horizontal a vertical
        const pAyuda = overlayAyuda.querySelector('p');
        if(pAyuda) {
            pAyuda.innerText = window.innerWidth > 1024 ? 'Haz clic y arrastra para mirar alrededor' : 'Desliza para mirar alrededor';
        }
    };

    // Escuchamos más eventos para detectar interacción genuina
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('click', onClick);
    window.addEventListener('touchstart', resetearInactividad, {passive: true}); // Para móviles
    window.addEventListener('touchmove', resetearInactividad, {passive: true}); // Para móviles
    window.addEventListener('wheel', resetearInactividad, {passive: true});
    window.addEventListener('resize', onResize);

    // Iniciar temporizador la primera vez
    resetearInactividad();

    // --- FUNCIÓN PARA CARGAR UN NODO ---
    function cargarNodo(idNodo, yawLlegada = null) {
        const nodoData = mapa.nodos[idNodo];
        if (!nodoData) return;
        tooltipUI.classList.add('oculto');
        console.log(`%c📍 Nodo actual: ${idNodo} | Título: ${nodoData.titulo}`, "color: #00d2ff; font-weight: bold; font-size: 14px;");
        tituloUI.innerText = nodoData.titulo;
        
        window.contextoActual = nodoData.contexto_ia || `Estás en ${nodoData.titulo}`;

        const anguloGiro = yawLlegada !== null ? yawLlegada : (nodoData.yaw_inicio || 0);

        const telon = document.getElementById('cortinilla-transicion');
        telon.style.opacity = '1';

        setTimeout(() => {
            cargadorTextura.load(nodoData.imagen_url, (textura) => {
                if (esfera.material.map) {
                    esfera.material.map.dispose(); 
                }
                textura.colorSpace = THREE.SRGBColorSpace;
                textura.generateMipmaps = false; 
                textura.minFilter = THREE.LinearFilter;
                esfera.material.map = textura;
                esfera.material.needsUpdate = true;

                esfera.rotation.y = 0;
                grupoHotspots.rotation.y = 0;

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
                        escalaObjetivo: 35
                    };

                    grupoHotspots.add(sprite);
                });

                const rotacionRadianes = anguloGiro * (Math.PI / 180);
                esfera.rotation.y = -rotacionRadianes;
                grupoHotspots.rotation.y = -rotacionRadianes;

                // 1. MOVER ARRIBA: Reseteamos los controles ANTES de aplicar el efecto
                controles.reset(); 

                // --- LÓGICA DEL LITTLE PLANET ---
                if (esPrimerNodo) {
                    camara.fov = 140; 
                    
                    // Apagamos la resistencia del ratón temporalmente para que la cámara pueda animarse
                    controles.enableDamping = false; 
                    animandoPlaneta = true;
                    
                    // Usamos 0.001 en Z para evitar el "Gimbal Lock" (bloqueo matemático) de Three.js
                    camara.position.set(0, 400, 0.001); 
                    posicionObjetivoCamara.set(0, 0, 0.1); 
                    
                    camara.updateProjectionMatrix();
                    fovObjetivo = 75; 
                    esPrimerNodo = false; 
                } else {
                    camara.fov = 75;
                    fovObjetivo = 75;
                    camara.position.set(0, 0, 0.1); 
                    posicionObjetivoCamara.set(0, 0, 0.1);
                    camara.updateProjectionMatrix();
                }

                // 2. Forzamos a los controles a reconocer la nueva posición
                controles.update(); 
                telon.style.opacity = '0';
                if (onNodeChange) onNodeChange(idNodo);
            });
        }, 200);
    }

    cargarNodo(mapa.nodo_inicial);

    // --- LOOP DE ANIMACIÓN ---
    let idAnimacion;

    function animar() {
        idAnimacion = requestAnimationFrame(animar);
        controles.update();
        const tiempo = Date.now() * 0.002;

        // --- PULSO Y ESCALA DE HOTSPOTS ---
        grupoHotspots.children.forEach(hs => {
            const escalaActual = hs.scale.x;
            const escalaDestino = hs.userData.escalaObjetivo;
            let nuevaEscala = escalaActual + (escalaDestino - escalaActual) * 0.1;

            if (escalaDestino === 35) {
                const pulso = Math.sin(tiempo) * 2;
                nuevaEscala += pulso;
            }

            hs.scale.set(nuevaEscala, nuevaEscala, 1);
        });

        // --- EFECTO TINY PLANET Y ZOOM SUAVE ---
        if (Math.abs(camara.fov - fovObjetivo) > 0.1) {
            camara.fov += (fovObjetivo - camara.fov) * 0.08; 
            camara.updateProjectionMatrix();
        }

        if (animandoPlaneta) {
            if (camara.position.distanceTo(posicionObjetivoCamara) > 0.01) {
                // Sigue cayendo hacia el centro
                camara.position.lerp(posicionObjetivoCamara, 0.08);
            } else {
                // ¡Aterrizó! Apagamos la animación y devolvemos el control suave al usuario
                animandoPlaneta = false;
                controles.enableDamping = true;
            }
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

    // --- ZOOM (via FOV) ---
    function hacerZoom(cantidad) {
        const ajuste = cantidad < 0 ? -5 : 5;
        fovObjetivo += ajuste;
        fovObjetivo = THREE.MathUtils.clamp(fovObjetivo, 30, 90);
    }

    // --- DESTRUIR VISOR ---
    function destruirVisor() {
        cancelAnimationFrame(idAnimacion);

        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('click', onClick);
        window.removeEventListener('resize', onResize);

        if (renderizador.domElement.parentNode) {
            renderizador.domElement.parentNode.removeChild(renderizador.domElement);
        }

        grupoHotspots.clear();
        escena.clear();
        geometria.dispose();
        material.dispose();
        if (mapaIcono) mapaIcono.dispose();
        controles.dispose();
        renderizador.dispose();

        console.log("🗑️ Visor destruido y memoria liberada.");
    }

    return { cargarNodo, hacerZoom, destruirVisor };
}