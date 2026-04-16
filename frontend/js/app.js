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