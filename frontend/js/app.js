import { iniciarVisor } from './three_core/scene.js';

// Contexto inicial de Jasper antes de entrar a un recorrido
window.contextoActual = "El usuario está en el Lobby Principal de la aplicación. Aún no ha iniciado ningún recorrido. Dale la bienvenida al IPN Virtual 360 e invítalo a seleccionar un laboratorio en el menú principal de su pantalla.";

const menuInicio = document.getElementById('menu-inicio');
const botonesRecorrido = document.querySelectorAll('.btn-recorrido');

// Escuchamos los clics en los botones del menú
botonesRecorrido.forEach(boton => {
    boton.addEventListener('click', () => {
        const labSeleccionado = boton.getAttribute('data-lab');
        cargarRecorrido(labSeleccionado);
    });
});

let visorActual = null;

async function cargarRecorrido(nombreLab) {
    try {
        if (visorActual && visorActual.destruirVisor) {
            visorActual.destruirVisor();
        }
        
        // Cambiamos el texto temporalmente para que el usuario sepa que está cargando
        document.querySelector('.titulo-main').innerText = "Cargando recorrido...";
        
        const respuesta = await fetch(`/visor_v2/data/${nombreLab}.json`);
        if (!respuesta.ok) throw new Error("Laboratorio no encontrado");

        const mapa = await respuesta.json();
        visorActual = iniciarVisor(mapa, (idNodoActual) => {
            actualizarCarruselActivo(idNodoActual);
            
            if (carruselContainer.classList.contains('oculto')) {
                carruselContainer.classList.remove('oculto');
                
                setTimeout(() => {
                    carruselContainer.classList.remove('colapsado');
                    document.body.classList.add('carrusel-abierto');
                }, 50);
            }
        });
        renderizarCarrusel(mapa);
        carruselContainer.classList.add('oculto');
        carruselContainer.classList.add('colapsado');
        document.body.classList.remove('carrusel-abierto');

        const chatContainer = document.getElementById('chat-container');
        chatContainer.classList.add('oculto');
        
        // Ocultamos el menú inicial con una animación
        menuInicio.style.opacity = '0';
        setTimeout(() => {
            menuInicio.style.display = 'none';
        }, 500);
        
    } catch (error) {
        console.error("Error al arrancar:", error);
        document.getElementById('titulo-ubicacion').innerText = "Error: Recorrido no encontrado";
        document.documentElement.classList.remove('modo-iframe');
        const menuInicio = document.getElementById('menu-inicio');
        if (menuInicio) {
            menuInicio.style.display = 'flex';
            setTimeout(() => menuInicio.style.opacity = '1', 50);
        }
    }
}

// --- CONTROLES DE VISOR ---
document.getElementById('btn-zoom-in').addEventListener('click', () => {
    if (visorActual) visorActual.hacerZoom(-10); // Reducir FOV = Acercar
});

document.getElementById('btn-zoom-out').addEventListener('click', () => {
    if (visorActual) visorActual.hacerZoom(10); // Aumentar FOV = Alejar
});

document.getElementById('btn-fullscreen').addEventListener('click', () => {
    if (!document.fullscreenElement) {
        document.body.requestFullscreen().catch(err => {
            console.error("Error al intentar entrar a pantalla completa:", err);
        });
    } else {
        document.exitFullscreen();
    }
});

// --- BOTÓN HOME ---
const btnHome = document.getElementById('btn-home');
const btnToggle = document.getElementById('btn-chat-toggle');
const btnClose = document.getElementById('btn-chat-close');
const chatContainer = document.getElementById('chat-container');
const btnSend = document.getElementById('btn-chat-send');
const inputChat = document.getElementById('chat-input');
const messagesDiv = document.getElementById('chat-messages');
const carruselContainer = document.getElementById('carrusel-container');
const carruselScroll = document.getElementById('carrusel-scroll');
const btnToggleCarrusel = document.getElementById('btn-toggle-carrusel');
const iconoCarrusel = document.getElementById('icono-carrusel');

btnHome.addEventListener('click', () => {
    // 1. Mostrar el menú de inicio con animación
    const menuInicio = document.getElementById('menu-inicio');
    menuInicio.style.display = 'flex';
    

    setTimeout(() => {
        menuInicio.style.opacity = '1';
    }, 10);

    carruselContainer.classList.add('oculto');
    document.body.classList.remove('carrusel-abierto');

    // 2. Mostrar el chat automáticamente
    document.getElementById('chat-container').classList.add('oculto');

    // 3. Actualizar el contexto
    window.contextoActual = "El usuario ha regresado al Lobby Principal. Invítalo de nuevo a seleccionar un laboratorio.";

    // 4. Mensaje automático de Jasper
    agregarMensajeUI(
        "Has vuelto al menú principal. ¿A qué otra escuela te gustaría ir?",
        "agente"
    );
});

function toggleChat() {
    chatContainer.classList.toggle('oculto');
}

// --- MOTOR DE ARRASTRE MAGNÉTICO PARA JASPER ---
let isDragging = false;
let isDraggingAction = false; 
let startX = 0; // Guardará dónde empezó el toque
let startY = 0;

// 1. Cuando el usuario presiona el botón
btnToggle.addEventListener('pointerdown', (e) => {
    isDragging = true;
    isDraggingAction = false;
    startX = e.clientX; // Guardamos X inicial
    startY = e.clientY; // Guardamos Y inicial
    btnToggle.classList.add('arrastrando');
    btnToggle.setPointerCapture(e.pointerId);
});

// 2. Mientras mueve el mouse/dedo
btnToggle.addEventListener('pointermove', (e) => {
    if (!isDragging) return;
    
    // Calculamos cuántos píxeles se movió realmente el dedo
    const diffX = Math.abs(e.clientX - startX);
    const diffY = Math.abs(e.clientY - startY);

    // ZONA MUERTA: Solo es un arrastre si se movió más de 5 píxeles
    if (diffX > 5 || diffY > 5) {
        isDraggingAction = true; 
        
        btnToggle.style.left = (e.clientX - btnToggle.offsetWidth / 2) + 'px';
        btnToggle.style.top = (e.clientY - btnToggle.offsetHeight / 2) + 'px';
        btnToggle.style.right = 'auto'; 
        btnToggle.style.bottom = 'auto'; 
    }
});

// 3. Cuando suelta el botón (¡ESTO TE FALTABA!)
btnToggle.addEventListener('pointerup', (e) => {
    if (!isDragging) return;
    isDragging = false;
    btnToggle.classList.remove('arrastrando');

    // Calculamos si lo soltó en la mitad izquierda o derecha
    const mitadPantalla = window.innerWidth / 2;
    
    if (e.clientX < mitadPantalla) {
        // IMÁN A LA IZQUIERDA
        btnToggle.style.left = '20px';
        chatContainer.classList.add('anclado-izquierda');
    } else {
        // IMÁN A LA DERECHA
        btnToggle.style.left = 'calc(100vw - 70px)'; 
        chatContainer.classList.remove('anclado-izquierda');
    }

    // El eje Y (arriba/abajo) lo dejamos donde lo soltó
    const maxTop = window.innerHeight - btnToggle.offsetHeight - 20;
    let finalTop = Math.max(20, Math.min(e.clientY, maxTop));
    btnToggle.style.top = finalTop + 'px';
});

// 4. El manejador del Click para abrir el chat (¡ESTO TAMBIÉN TE FALTABA!)
btnToggle.addEventListener('click', (e) => {
    // Si fue un arrastre, ignoramos el click. Si fue un toque rápido, abrimos el chat.
    if (isDraggingAction) {
        e.preventDefault();
    } else {
        toggleChat();
    }
});
btnClose.addEventListener('click', toggleChat);

// --- CONTADOR GLOBAL PARA IDs ÚNICOS DE MENSAJES ---
let sessionId = null;
let contadorMensajes = 0;

function inicializarSesion() {
    const datosGuardados = JSON.parse(localStorage.getItem('chat_session'));
    if (datosGuardados && Date.now() < datosGuardados.expira) {
        sessionId = datosGuardados.id;
        console.log("Sesión recuperada:", sessionId);
    } else {
        // Si no hay datos o ya pasaron las 72 horas, limpiamos
        localStorage.removeItem('chat_session');
        sessionId = null;
        console.log("Sesión nueva iniciada");
    }
}
inicializarSesion();

async function enviarMensaje() {
    const texto = inputChat.value.trim();
    if (!texto) return;

    agregarMensajeUI(texto, 'usuario');
    inputChat.value = '';

    const idCarga = agregarMensajeUI('...', 'agente');

    try {
        const response = await fetch('/api_v2/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mensaje: texto,
                contexto: window.contextoActual,
                session_id: sessionId // <--- 1. Enviamos el ID actual (sea null o un string)
            })
        });

        const data = await response.json();
        
        // 2. Guardamos el session_id que nos envía el backend
        // Si el backend genera uno nuevo, lo guardamos para la próxima vuelta.
        if (data.session_id) {
            sessionId = data.session_id; // Actualiza la variable
            const sesionGuardar = {
                id: sessionId,
                expira: Date.now() + (72 * 60 * 60 * 1000) // Renueva las 72h
            };
            localStorage.setItem('chat_session', JSON.stringify(sesionGuardar));
        }
        // -----------------------------------------------------

        // Reemplazar el "Escribiendo..." con la respuesta real
        const elementoCarga = document.getElementById(idCarga);
        if (elementoCarga) {
            elementoCarga.innerText = data.respuesta;
        }
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

    } catch (error) {
        console.error('Error de chat:', error);
        const elementoCarga = document.getElementById(idCarga);
        if (elementoCarga) {
            elementoCarga.innerText = 'Error al conectar con Jasper.';
        }
    }
}

btnSend.addEventListener('click', enviarMensaje);
inputChat.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') enviarMensaje();
});

function agregarMensajeUI(texto, tipo) {
    const div = document.createElement('div');
    div.className = `msg ${tipo}`;
    div.innerText = texto;
    // Usamos un contador incremental en lugar de Date.now() para garantizar
    // que cada mensaje tenga siempre un ID único, sin importar qué tan rápido
    // se creen dos mensajes consecutivos.
    div.id = 'msg-' + (++contadorMensajes);
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return div.id;
}

// --- LÓGICA DEL CARRUSEL ---

function renderizarCarrusel(mapa) {
    carruselScroll.innerHTML = ''; // Limpiar carrusel anterior

    Object.keys(mapa.nodos).forEach(idNodo => {
        const nodo = mapa.nodos[idNodo];

        const miniatura = document.createElement('div');
        miniatura.className = 'miniatura';
        miniatura.id = `thumb-${idNodo}`;

        // Usamos la imagen panorámica como miniatura (el CSS background-size: cover hace la magia)
        miniatura.style.backgroundImage = `url('${nodo.imagen_url}')`;

        const titulo = document.createElement('div');
        titulo.className = 'miniatura-titulo';
        titulo.innerText = nodo.titulo;
        titulo.title = nodo.titulo; // Tooltip nativo por si el texto es muy largo

        miniatura.appendChild(titulo);

        // Evento para viajar a ese nodo al hacer clic
        miniatura.addEventListener('click', () => {
            if (visorActual && !miniatura.classList.contains('activa')) {
                // Opcional: Cerrar chat en móviles al navegar para ver bien la pantalla
                if (window.innerWidth <= 768) {
                    chatContainer.classList.add('oculto');
                }
                visorActual.cargarNodo(idNodo);
            }
        });

        carruselScroll.appendChild(miniatura);
    });
}

function actualizarCarruselActivo(idNodoActual) {
    // Quitar clase activa a todos
    document.querySelectorAll('.miniatura').forEach(thumb => {
        thumb.classList.remove('activa');
    });

    // Poner clase activa al nodo actual
    const miniaturaActiva = document.getElementById(`thumb-${idNodoActual}`);
    if (miniaturaActiva) {
        miniaturaActiva.classList.add('activa');
        // Hacer scroll automático para que la miniatura activa quede visible en el centro
        miniaturaActiva.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
}

// Botón para colapsar/expandir el carrusel
btnToggleCarrusel.addEventListener('click', () => {
    carruselContainer.classList.toggle('colapsado');

    if (carruselContainer.classList.contains('colapsado')) {
        iconoCarrusel.innerText = 'expand_less'; // Flecha hacia arriba
        document.body.classList.remove('carrusel-abierto');
    } else {
        iconoCarrusel.innerText = 'expand_more'; // Flecha hacia abajo
        document.body.classList.add('carrusel-abierto');
    }
});


// --- AUTO-CARGA DESDE LA URL ---
document.addEventListener('DOMContentLoaded', () => {
    const parametros = new URLSearchParams(window.location.search);
    const labCrudo = parametros.get('lab');
    const labRequerido = labCrudo ? labCrudo.replace(/[^a-zA-Z0-9-]/g, '') : null;

    if (labRequerido) {
        // 1. Ocultamos el menú de un golpe y sin animación
        const menuInicio = document.getElementById('menu-inicio');
        if (menuInicio) {
            menuInicio.style.transition = 'none'; // Apagamos animaciones
            menuInicio.style.opacity = '0';
            menuInicio.style.display = 'none';
        }

        // 2. Cargamos el recorrido
        cargarRecorrido(labRequerido);
    }
});