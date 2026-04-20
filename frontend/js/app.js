import { iniciarVisor } from './three_core/scene.js';

async function arrancarAplicacion() {
    try {
        const params = new URLSearchParams(window.location.search);
        const nombreLab = params.get('lab') || 'lanta';
        const respuesta = await fetch(`/data/${nombreLab}.json`);
        if (!respuesta.ok) throw new Error("Laboratorio no encontrado");

        const mapa = await respuesta.json();
        const visorController = iniciarVisor(mapa);
        
        // Zoom
        document.getElementById('btn-zoom-in').addEventListener('click', () => {
            visorController.hacerZoom(-10); // Reducir FOV = Acercar
        });

        document.getElementById('btn-zoom-out').addEventListener('click', () => {
            visorController.hacerZoom(10); // Aumentar FOV = Alejar
        });

        // Pantalla Completa
        document.getElementById('btn-fullscreen').addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.body.requestFullscreen().catch(err => {
                    console.error("Error al intentar entrar a pantalla completa:", err);
                });
            } else {
                document.exitFullscreen();
            }
        });
        
    } catch (error) {
        console.error("Error al arrancar:", error);
        document.getElementById('titulo-ubicacion').innerText = "Error: Recorrido no encontrado";
    }
}

arrancarAplicacion();

const btnToggle = document.getElementById('btn-chat-toggle');
const btnClose = document.getElementById('btn-chat-close');
const chatContainer = document.getElementById('chat-container');
const btnSend = document.getElementById('btn-chat-send');
const inputChat = document.getElementById('chat-input');
const messagesDiv = document.getElementById('chat-messages');

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