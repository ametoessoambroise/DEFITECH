import os
import uuid
import logging
import requests
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from queue import Queue
import time
import io
import base64
from app.utils.cloudinary_utils import upload_to_cloudinary

# Configuration du logging
logger = logging.getLogger(__name__)


# Récupération de la clé d'API (doit être configurée dans l'environnement)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


class GeminiImageGenerator:
    """Générateur d'images utilisant l'API Imagen 3 de Google"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = "imagen-4.0-generate-001"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:predict"
        self.queue = Queue()
        self.results = {}
        self.running = False
        self.worker_thread = None

    def start_worker(self):
        """Démarre le worker de traitement en arrière-plan"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.running = True
            self.worker_thread = threading.Thread(
                target=self._process_queue, daemon=True
            )
            self.worker_thread.start()
            logger.info("Worker de génération d'images Gemini démarré")

    def stop_worker(self):
        """Arrête le worker"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)

    def add_task(self, prompt: str, conversation_id: int) -> str:
        """Ajoute une tâche de génération à la file d'attente"""
        task_id = str(uuid.uuid4())
        self.results[task_id] = {
            "status": "pending",
            "progress": 0,
            "conversation_id": conversation_id,
        }
        self.queue.put((task_id, prompt, conversation_id))

        # S'assurer que le worker tourne
        self.start_worker()

        return task_id

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """Récupère le statut d'une tâche"""
        return self.results.get(task_id, {"status": "not_found"})

    def _process_queue(self):
        """Boucle de traitement des tâches"""
        while self.running:
            try:
                # Attente non bloquante pour pouvoir s'arrêter
                if self.queue.empty():
                    time.sleep(1)
                    continue

                task_id, prompt, conversation_id = self.queue.get()
                self.results[task_id]["status"] = "processing"
                logger.info(f"Traitement tâche {task_id}: {prompt[:50]}...")

                image_url = self._generate_with_gemini(prompt, conversation_id)

                if image_url:
                    self.results[task_id].update(
                        {
                            "status": "completed",
                            "progress": 100,
                            "url": image_url,
                            "completed_at": datetime.utcnow().isoformat(),
                        }
                    )
                    logger.info(f"Tâche {task_id} terminée avec succès: {image_url}")
                else:
                    self.results[task_id].update(
                        {"status": "failed", "error": "La génération a échoué"}
                    )
                    logger.error(f"Tâche {task_id} a échoué")

                self.queue.task_done()
            except Exception as e:
                logger.error(f"Erreur dans le worker d'images: {e}")
                time.sleep(2)

    def _generate_with_gemini(self, prompt: str, conversation_id: int) -> Optional[str]:
        """Appel effectif à l'API Imagen 3 et upload sur Cloudinary"""
        if not self.api_key:
            logger.error("Clé API Gemini manquante pour la génération d'images")
            return None

        headers = {"Content-Type": "application/json"}

        # Construction du payload pour Imagen 3
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "1:1"},
        }

        try:
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code == 200:
                result = response.json()
                predictions = result.get("predictions", [])
                if predictions and "bytesBase64Encoded" in predictions[0]:
                    img_data = base64.b64decode(predictions[0]["bytesBase64Encoded"])

                    # Upload direct sur Cloudinary
                    filename = f"gen_{uuid.uuid4().hex[:8]}.png"
                    upload_result = upload_to_cloudinary(
                        io.BytesIO(img_data),
                        filename,
                        folder=f"ai_gen/{conversation_id}",
                        resource_type="image",
                    )
                    return upload_result.get("secure_url")
                else:
                    logger.error(f"Format de réponse inattendu: {result}")
            else:
                logger.error(
                    f"Erreur API Gemini Image ({response.status_code}): {response.text}"
                )

        except Exception as e:
            logger.error(f"Exception lors de l'appel Gemini Image: {e}")

        return None


# Singleton pour le générateur
_generator = None


def get_generator():
    """Récupère l'instance unique du générateur"""
    global _generator
    if _generator is None:
        _generator = GeminiImageGenerator()
    return _generator


def generate_image_async(prompt: str, conversation_id: int) -> Dict[str, Any]:
    """Point d'entrée pour la génération asynchrone"""
    try:
        generator = get_generator()
        task_id = generator.add_task(prompt, conversation_id)

        return {
            "type": "generated_image",
            "prompt": prompt,
            "status": "generating",
            "task_id": task_id,
            "created_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de la tâche de génération: {e}")
        return {
            "type": "generated_image",
            "status": "error",
            "error": str(e),
            "task_id": str(uuid.uuid4()),
        }


def check_image_status(task_id: str) -> Dict[str, Any]:
    """Récupère le statut d'une génération en cours"""
    generator = get_generator()
    return generator.get_status(task_id)
