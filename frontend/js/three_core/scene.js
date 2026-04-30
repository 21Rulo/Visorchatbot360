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

// --- FLECHAS DE BORDE (CSS puro, sin imagen) ---
function crearFlechaBorde() {
    const el = document.createElement('div');
    el.style.cssText = `
        position: fixed;
        width: 0;
        height: 0;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease;
        z-index: 40;
        filter: drop-shadow(0 0 6px rgba(97, 203, 53, 0.9));
    `;
    document.body.appendChild(el);
    return el;
}

function estilizarFlecha(el, direccion) {
    const color = 'rgba(97, 203, 53, 0.95)';
    const size = '20px';
    const pad = '18px';

    // Limpiar estilos anteriores
    el.style.borderTop = el.style.borderBottom = el.style.borderLeft = el.style.borderRight = 'none';
    el.style.top = el.style.bottom = el.style.left = el.style.right = '';
    el.style.transform = '';

    switch (direccion) {
        case 'derecha':
            el.style.borderTop    = `${size} solid transparent`;
            el.style.borderBottom = `${size} solid transparent`;
            el.style.borderLeft   = `${size} solid ${color}`;
            el.style.right = pad;
            break;
        case 'izquierda':
            el.style.borderTop    = `${size} solid transparent`;
            el.style.borderBottom = `${size} solid transparent`;
            el.style.borderRight  = `${size} solid ${color}`;
            el.style.left = pad;
            break;
        case 'arriba':
            el.style.borderLeft   = `${size} solid transparent`;
            el.style.borderRight  = `${size} solid transparent`;
            el.style.borderBottom = `${size} solid ${color}`;
            el.style.top = pad;
            break;
        case 'abajo':
            el.style.borderLeft   = `${size} solid transparent`;
            el.style.borderRight  = `${size} solid transparent`;
            el.style.borderTop    = `${size} solid ${color}`;
            el.style.bottom = pad;
            break;
    }
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
    controles.rotateSpeed = 0.4;   // Menor = más lento
    controles.enableDamping = true; // Inercia al soltar
    controles.dampingFactor = 0.05;

    const geometria = new THREE.SphereGeometry(500, 60, 40);
    geometria.scale(-1, 1, 1);
    const cargadorTextura = new THREE.TextureLoader();
    const mapaIcono = cargadorTextura.load('/assets/src/arrow1.png',
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

    // --- POOL DE FLECHAS DE BORDE ---
    const MAX_FLECHAS = 8;
    const poolFlechas = Array.from({ length: MAX_FLECHAS }, () => crearFlechaBorde());

    function ocultarTodasFlechas() {
        poolFlechas.forEach(f => { f.style.opacity = '0'; });
    }


    let ultimoHotspotTocado = null;
    // --- RAYCASTER ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseMove = (event) => {
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
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, camara);

        const intersecciones = raycaster.intersectObjects(grupoHotspots.children);
        
        if (intersecciones.length > 0) {
            const hotspotTocado = intersecciones[0].object;
            const idDestino = hotspotTocado.userData.destino;
            const yawLlegada = hotspotTocado.userData.yaw_llegada ?? 0;

            // --- LÓGICA PARA MÓVILES ---
            // Si es el mismo que ya tocamos (segundo toque) o si estamos en PC (mousemove ya mostró el tooltip)
            if (ultimoHotspotTocado === hotspotTocado || window.innerWidth > 1024) {
                tooltipUI.classList.add('oculto');
                cargarNodo(idDestino, yawLlegada);
                ultimoHotspotTocado = null;
            } else {
                // Primer toque en móvil: mostramos el tooltip
                ultimoHotspotTocado = hotspotTocado;
                tooltipUI.innerText = hotspotTocado.userData.texto;
                tooltipUI.style.left = `${event.clientX}px`;
                tooltipUI.style.top = `${event.clientY - 40}px`; // Un poco más arriba para que el dedo no lo tape
                tooltipUI.classList.remove('oculto');
                
                // Si el usuario toca otra parte de la pantalla, se limpia el rastro
                setTimeout(() => {
                    if (ultimoHotspotTocado === hotspotTocado) ultimoHotspotTocado = null;
                }, 3000);
            }
            return;
        }
        tooltipUI.classList.add('oculto');
        ultimoHotspotTocado = null;

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
    };

    const onResize = () => {
        camara.aspect = window.innerWidth / window.innerHeight;
        camara.updateProjectionMatrix();
        renderizador.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('click', onClick);
    window.addEventListener('resize', onResize);

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
                esfera.material.map = textura;
                esfera.material.needsUpdate = true;

                esfera.rotation.y = 0;
                grupoHotspots.rotation.y = 0;

                grupoHotspots.clear();
                ocultarTodasFlechas();

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

                controles.reset();
                telon.style.opacity = '0';
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

        // --- INDICADORES DE BORDE ---
        // Si el menú de inicio está visible, ocultamos las flechas y no las procesamos
        const menuInicio = document.getElementById('menu-inicio');
        const menuVisible = menuInicio && menuInicio.style.display !== 'none';

        if (menuVisible) {
            ocultarTodasFlechas();
        } else {
            ocultarTodasFlechas();
            let indiceFlechaActual = 0;

            grupoHotspots.children.forEach(hs => {
                if (indiceFlechaActual >= MAX_FLECHAS) return;

                const vector = hs.position.clone();
                vector.project(camara);

                const detras = vector.z > 1;
                const fueraX = vector.x > 1 || vector.x < -1;
                const fueraY = vector.y > 1 || vector.y < -1;
                const estaFuera = detras || fueraX || fueraY;

                if (!estaFuera) return;

                const flecha = poolFlechas[indiceFlechaActual];
                indiceFlechaActual++;

                let direccion;
                if (detras) {
                    direccion = vector.x >= 0 ? 'izquierda' : 'derecha';
                } else {
                    const absX = Math.abs(vector.x);
                    const absY = Math.abs(vector.y);
                    if (absX >= absY) {
                        direccion = vector.x > 0 ? 'derecha' : 'izquierda';
                    } else {
                        direccion = vector.y > 0 ? 'arriba' : 'abajo';
                    }
                }

                estilizarFlecha(flecha, direccion);

                if (direccion === 'derecha' || direccion === 'izquierda') {
                    flecha.style.top = '50%';
                    flecha.style.transform = 'translateY(-50%)';
                } else {
                    flecha.style.left = '50%';
                    flecha.style.transform = 'translateX(-50%)';
                }

                const pulsoOpacidad = 0.6 + Math.sin(tiempo * 2) * 0.4;
                flecha.style.opacity = String(pulsoOpacidad);
            });
        }

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

        poolFlechas.forEach(f => {
            if (f.parentNode) f.parentNode.removeChild(f);
        });

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