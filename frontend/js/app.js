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
        
        const respuesta = await fetch(`/data/${nombreLab}.json`);
        if (!respuesta.ok) throw new Error("Laboratorio no encontrado");

        const mapa = await respuesta.json();
        visorActual = iniciarVisor(mapa);

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
    }
}

// --- CONTROLES DE VISOR ---
// Registrados una sola vez, delegan en visorActual para evitar listeners duplicados

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

btnHome.addEventListener('click', () => {
    // 1. Mostrar el menú de inicio con animación
    const menuInicio = document.getElementById('menu-inicio');
    menuInicio.style.display = 'flex';

    setTimeout(() => {
        menuInicio.style.opacity = '1';
    }, 10);

    // 2. Mostrar el chat automáticamente
    document.getElementById('chat-container').classList.remove('oculto');

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

btnToggle.addEventListener('click', toggleChat);
btnClose.addEventListener('click', toggleChat);

async function enviarMensaje() {
    const texto = inputChat.value.trim();
    if (!texto) return;

    // Mostrar mensaje del usuario
    agregarMensajeUI(texto, 'usuario');
    inputChat.value = '';

    // Mostrar "Escribiendo..."
    const idCarga = agregarMensajeUI('...', 'agente');

    try {
        // Enviar al backend (Asegúrate de que el puerto coincida con tu backend)
        const response = await fetch('http://127.0.0.1:8000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mensaje: texto,
                contexto: window.contextoActual // ¡Aquí le pasamos el contexto del JSON!
            })
        });

        const data = await response.json();
        
        // Reemplazar el "Escribiendo..." con la respuesta real
        document.getElementById(idCarga).innerText = data.respuesta;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

    } catch (error) {
        console.error('Error de chat:', error);
        document.getElementById(idCarga).innerText = 'Error al conectar con Jasper.';
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
    div.id = 'msg-' + Date.now();
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return div.id;
}