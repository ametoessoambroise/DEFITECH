# ai_image_generator.py
"""
Module optimisé pour la génération d'images avec Stable Diffusion
Gestion asynchrone, économie de mémoire, et file d'attente
"""

import os
import uuid
import logging
import threading
from datetime import datetime
from queue import Queue
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class ImageGenerationQueue:
    """Gestionnaire de file d'attente pour génération d'images"""

    def __init__(self):
        self.queue = Queue()
        self.results = {}
        self.pipeline = None
        self.is_loading = False
        self.worker_thread = None
        self.running = False
        self.cleanup_thread = None

    def start_worker(self):
        """Démarre le worker de traitement en arrière-plan"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.running = True
            self.worker_thread = threading.Thread(
                target=self._process_queue, daemon=True
            )
            self.worker_thread.start()
            logger.info("Worker de génération d'images démarré")

            # Démarrer le thread de nettoyage
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop, daemon=True
            )
            self.cleanup_thread.start()
            logger.info("Thread de nettoyage démarré")

    def stop_worker(self):
        """Arrête le worker proprement"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
            logger.info("Worker de génération d'images arrêté")

    def _cleanup_loop(self):
        """Nettoie périodiquement les résultats expirés"""
        import time

        while self.running:
            time.sleep(300)  # Toutes les 5 minutes
            self.cleanup_old_results(max_age_minutes=30)

    def _load_pipeline(self) -> bool:
        """Charge le pipeline de manière optimisée"""
        if self.pipeline is not None:
            return True

        if self.is_loading:
            return False

        try:
            self.is_loading = True
            logger.info("Chargement du modèle Stable Diffusion Turbo...")

            # Import lazy loading for heavy libraries
            import torch
            from diffusers import AutoPipelineForText2Image

            # Vérifier la mémoire disponible
            import psutil

            available_memory = psutil.virtual_memory().available / (1024**3)  # GB

            if available_memory < 4:
                logger.warning(
                    f"Mémoire disponible insuffisante: {available_memory:.1f}GB"
                )
                return False

            # Charger avec optimisations mémoire
            self.pipeline = AutoPipelineForText2Image.from_pretrained(
                "stabilityai/sd-turbo",
                torch_dtype=torch.float16,
                safety_checker=None,
                requires_safety_checker=False,
            )

            # Forcer sur CPU avec optimisations
            self.pipeline = self.pipeline.to("cpu")
            self.pipeline.enable_attention_slicing()
            self.pipeline.enable_vae_slicing()

            if hasattr(self.pipeline, "enable_sequential_cpu_offload"):
                self.pipeline.enable_sequential_cpu_offload()

            logger.info("Modèle chargé avec succès (optimisé float16)")
            return True

        except MemoryError as e:
            logger.error(f"MemoryError lors du chargement du modèle: {e}")
            self.pipeline = None
            return False
        except Exception as e:
            logger.error(f"Erreur chargement pipeline: {e}")
            self.pipeline = None
            return False
        finally:
            self.is_loading = False

    def _process_queue(self):
        """Traite les demandes de génération en file d'attente"""
        while self.running:
            try:
                if self.queue.empty():
                    import time

                    time.sleep(1)
                    continue

                task = self.queue.get(timeout=1)
                task_id = task["id"]

                logger.info(f"Traitement de la tâche {task_id}")

                # Charger le pipeline si nécessaire
                if not self._load_pipeline():
                    self.results[task_id] = {
                        "status": "error",
                        "error": "Impossible de charger le modèle (mémoire insuffisante)",
                    }
                    self.queue.task_done()
                    continue

                # Générer l'image
                try:
                    prompt = task["prompt"]
                    filepath = task["filepath"]

                    logger.info(f"Génération image: {prompt[:50]}...")

                    # Génération avec paramètres optimisés
                    image = self.pipeline(
                        prompt,
                        num_inference_steps=2,
                        guidance_scale=0.0,
                        height=512,
                        width=512,
                    ).images[0]

                    # Sauvegarder
                    image.save(filepath)

                    self.results[task_id] = {
                        "status": "completed",
                        "filepath": filepath,
                        "filename": os.path.basename(filepath),
                        "completed_at": datetime.utcnow().isoformat(),
                    }

                    logger.info(f"Image générée avec succès: {filepath}")

                except Exception as e:
                    logger.error(f"Erreur génération image: {e}")
                    self.results[task_id] = {"status": "error", "error": str(e)}

                self.queue.task_done()

            except Exception as e:
                logger.error(f"Erreur traitement queue: {e}")
                continue

    def add_task(self, prompt: str, filepath: str) -> str:
        """Ajoute une tâche de génération à la file"""
        task_id = str(uuid.uuid4())

        task = {
            "id": task_id,
            "prompt": prompt,
            "filepath": filepath,
            "created_at": datetime.utcnow(),
        }

        self.queue.put(task)
        self.results[task_id] = {"status": "queued", "created_at": datetime.utcnow()}

        logger.info(f"Tâche {task_id} ajoutée à la file (taille: {self.queue.qsize()})")

        return task_id

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le résultat d'une tâche"""
        return self.results.get(task_id)

    def cleanup_old_results(self, max_age_minutes: int = 30):
        """Nettoie les anciens résultats"""
        now = datetime.utcnow()
        to_remove = []

        for task_id, result in self.results.items():
            if "created_at" in result:
                created_at = result["created_at"]
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)

                age = (now - created_at).total_seconds() / 60
                if age > max_age_minutes:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.results[task_id]

        if to_remove:
            logger.info(f"Nettoyage de {len(to_remove)} résultats expirés")

    def get_queue_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la queue"""
        return {
            "queue_size": self.queue.qsize(),
            "total_results": len(self.results),
            "pipeline_loaded": self.pipeline is not None,
            "is_loading": self.is_loading,
        }


# Instance globale
_image_queue = None


def get_image_queue() -> ImageGenerationQueue:
    """Récupère l'instance globale de la queue"""
    global _image_queue
    if _image_queue is None:
        _image_queue = ImageGenerationQueue()
        _image_queue.start_worker()
    return _image_queue


def generate_image_async(
    prompt: str, conversation_id: int, upload_folder: str
) -> Dict[str, Any]:
    """
    Génère une image de manière asynchrone
    Retourne immédiatement avec un statut 'generating'
    """
    try:
        # CORRECTION: Utiliser le chemin sans duplication
        # Le upload_folder contient déjà 'uploads', donc on ajoute juste 'ai_attachments'
        upload_dir = os.path.join(
            upload_folder,  # 'uploads' déjà inclus
            "ai_attachments",
            str(conversation_id),
        )
        os.makedirs(upload_dir, exist_ok=True)

        # Créer le nom de fichier
        filename = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
        )
        filepath = os.path.abspath(os.path.join(upload_dir, filename))

        # Ajouter à la file d'attente
        queue = get_image_queue()
        task_id = queue.add_task(prompt, filepath)

        return {
            "type": "generated_image",
            "name": filename,
            "prompt": prompt,
            "status": "generating",
            "task_id": task_id,  # TOUJOURS inclure task_id
            "created_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erreur ajout tâche génération: {e}")
        return {
            "type": "generated_image",
            "status": "error",
            "error": str(e),
            "task_id": str(uuid.uuid4()),  # Task ID même en cas d'erreur
        }


def check_image_status(task_id: str) -> Dict[str, Any]:
    """Vérifie le statut d'une génération d'image"""
    queue = get_image_queue()
    result = queue.get_result(task_id)

    if result is None:
        return {"status": "not_found"}

    # Enrichir avec les stats de la queue si en attente
    if result.get("status") == "queued":
        stats = queue.get_queue_stats()
        result["queue_position"] = stats["queue_size"]

    return result


def generate_placeholder_image(description: str, filepath: str) -> bool:
    """Génère une image placeholder simple avec PIL"""
    try:
        img_size = (512, 512)
        img = Image.new("RGB", img_size, color="#f0f8ff")
        draw = ImageDraw.Draw(img)

        # Cadre
        draw.rectangle(
            [10, 10, img_size[0] - 10, img_size[1] - 10], outline="#4a90e2", width=3
        )

        # Titre
        try:
            font_title = ImageFont.truetype("arial.ttf", 24)
            font_text = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()

        title = "Image Éducative"
        draw.text((50, 30), title, fill="#2c3e50", font=font_title)

        # Description (tronquée)
        max_width = img_size[0] - 100
        words = description.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}" if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font_text)
            if bbox[2] - bbox[0] < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # Limiter les lignes
        y_position = 100
        for line in lines[:10]:
            draw.text((50, y_position), line, fill="#34495e", font=font_text)
            y_position += 30

        img.save(filepath)
        return True

    except Exception as e:
        logger.error(f"Erreur génération placeholder: {e}")
        return False


def get_queue_stats() -> Dict[str, Any]:
    """Retourne les statistiques de la queue (pour monitoring)"""
    queue = get_image_queue()
    return queue.get_queue_stats()


def cleanup_worker():
    """Nettoie le worker à l'arrêt de l'application"""
    global _image_queue
    if _image_queue:
        _image_queue.stop_worker()
        _image_queue = None


# ============================================================================
# LoRA-BASED GENERATION (DreamShaper + Custom LoRA)
# ============================================================================

_lora_pipeline = None
_lora_loading = False


def load_lora_pipeline():
    """Charge le pipeline LoRA (DreamShaper + LoRA custom)"""
    global _lora_pipeline, _lora_loading

    if _lora_pipeline is not None:
        return _lora_pipeline

    if _lora_loading:
        return None

    try:
        _lora_loading = True
        logger.info("🎨 Chargement du modèle DreamShaper + LoRA...")

        # Lazy imports to avoid startup delay
        from diffusers import StableDiffusionPipeline
        import torch

        # Chemins des modèles
        base_model_path = "lora/models/dreamshaper/DreamShaper_8_pruned.safetensors"
        lora_weights_path = "lora/models/lora/lora.safetensors"

        # Vérifier que les fichiers existent
        if not os.path.exists(base_model_path):
            logger.error(f"❌ Modèle DreamShaper introuvable: {base_model_path}")
            return None

        if not os.path.exists(lora_weights_path):
            logger.warning(f"⚠️ LoRA weights introuvable: {lora_weights_path}")
            # Continuer sans LoRA

        # Charger le pipeline
        _lora_pipeline = StableDiffusionPipeline.from_single_file(
            base_model_path,
            torch_dtype=torch.float16,
            safety_checker=None,
            requires_safety_checker=False,
        ).to("cpu")

        # Charger les poids LoRA si disponibles
        if os.path.exists(lora_weights_path):
            _lora_pipeline.load_lora_weights(lora_weights_path)
            _lora_pipeline.fuse_lora(lora_scale=0.8)
            logger.info("✅ LoRA weights chargés et fusionnés")

        # Optimisations mémoire
        _lora_pipeline.enable_attention_slicing()
        _lora_pipeline.enable_vae_slicing()

        logger.info("✅ Pipeline LoRA chargé avec succès")
        return _lora_pipeline

    except Exception as e:
        logger.error(f"❌ Erreur chargement pipeline LoRA: {e}")
        _lora_pipeline = None
        return None
    finally:
        _lora_loading = False


def generate_with_lora(prompt: str, output_path: str, num_steps: int = 20) -> bool:
    """
    Génère une image avec le pipeline LoRA

    Args:
        prompt: Description de l'image
        output_path: Chemin de sauvegarde
        num_steps: Nombre d'étapes d'inférence (20 recommandé)

    Returns:
        True si succès, False sinon
    """
    try:
        import traceback

        logger.info(f"🎨 Tentative de génération LoRA pour: {prompt[:50]}...")

        pipeline = load_lora_pipeline()

        if pipeline is None:
            logger.error("❌ Pipeline LoRA non disponible")
            return False

        logger.info(f"✅ Pipeline chargé, génération en cours...")

        # Génération
        image = pipeline(
            prompt,
            num_inference_steps=num_steps,
            guidance_scale=7.5,
            height=512,
            width=512,
        ).images[0]

        # Sauvegarder
        image.save(output_path)
        logger.info(f"✅ Image LoRA générée avec succès: {output_path}")

        return True

    except Exception as e:
        import traceback

        logger.error(f"❌ Erreur génération LoRA: {e}")
        logger.error(f"Traceback complet:\n{traceback.format_exc()}")
        return False


import os

# Removed top-level tf/keras/numpy imports
import pickle
from PIL import Image
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIImageGenerator:
    def __init__(self, model_path, label_encoder_path):
        self.model_path = model_path
        self.label_encoder_path = label_encoder_path
        self.model = None
        self.label_to_index = None
        self.index_to_label = None
        self.image_size = (128, 128)  # Match MobileNetV2 expected input

    def load_model(self):
        """Loads the Keras model and label encoder if not already loaded."""
        if self.model is not None:
            return True

        try:
            # Lazy imports
            import numpy as np
            import tensorflow as tf
            from tensorflow import keras

            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found: {self.model_path}")
                return False

            self.model = keras.models.load_model(self.model_path)

            # Load label encoder
            if os.path.exists(self.label_encoder_path):
                with open(self.label_encoder_path, "rb") as f:
                    self.label_to_index = pickle.load(f)
                self.index_to_label = {v: k for k, v in self.label_to_index.items()}
            else:
                logger.warning("Label encoder not found. Using dummy labels.")
                self.label_to_index = {}

            logger.info("✅ AI Model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            return False

    def find_target_class(self, prompt):
        """Finds the best matching class index for the given prompt."""
        if not self.label_to_index:
            return 0  # Default to first class if no labels

        prompt = prompt.lower()
        best_match = None

        # Exact match attempt
        for label in self.label_to_index:
            if label.lower() in prompt:
                return self.label_to_index[label]

        # Fallback: Random class (for creativity)
        import random

        return (
            random.choice(list(self.label_to_index.values()))
            if self.label_to_index
            else 0
        )

    def generate_image(self, prompt, steps=100, step_size=0.01):
        """
        Generates an image using Activation Maximization (DeepDream style).
        """
        # Lazy imports needed for this method too
        import tensorflow as tf
        import numpy as np
        from PIL import Image

        if not self.load_model():
            raise RuntimeError("Model could not be loaded.")

        target_class_index = self.find_target_class(prompt)
        logger.info(
            f"🎨 Generating image for prompt: '{prompt}' (Target Class: {self.index_to_label.get(target_class_index, target_class_index)})"
        )

        # Start with random noise
        img = tf.random.uniform((1, *self.image_size, 3))
        img = (img - 0.5) * 0.25  # Center around 0, small variance

        # Optimization loop
        for i in range(steps):
            with tf.GradientTape() as tape:
                tape.watch(img)
                predictions = self.model(img)
                loss = predictions[0, target_class_index]

            # Get gradients of the loss with respect to the input image
            gradients = tape.gradient(loss, img)

            # Normalize gradients
            gradients /= tf.math.reduce_std(gradients) + 1e-8

            # Update image (Gradient Ascent)
            img += gradients * step_size

            # Clip pixel values
            img = tf.clip_by_value(img, 0.0, 1.0)

        # Convert tensor to PIL Image
        img_array = img[0].numpy()
        img_array = (img_array * 255).astype(np.uint8)
        pil_img = Image.fromarray(img_array)

        # Save to buffer
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")
        buf.seek(0)

        return buf
