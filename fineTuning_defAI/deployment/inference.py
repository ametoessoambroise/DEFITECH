"""
API d'inférence pour DefAI (Gemma 2B fine-tuné)
Expose le modèle via une API REST Flask/FastAPI pour utilisation dans la plateforme
"""

import os
import json
import logging
import torch
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass

# Flask
from flask import Flask, request, jsonify
from flask_cors import CORS

# Bibliothèques HuggingFace
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    pipeline
)
from peft import PeftModel

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InferenceConfig:
    """Configuration pour l'inférence"""
    model_path: str = "../model/gemma_finetuned"
    base_model_path: str = "google/gemma-2b"
    
    # Génération
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    do_sample: bool = True
    repetition_penalty: float = 1.1
    
    # API
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    
    # Device
    device: str = "auto"


class DefAIModel:
    """Wrapper pour le modèle DefAI"""
    
    def __init__(self, config: InferenceConfig):
        self.config = config
        self.device = self._get_device()
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        
        logger.info(f"Initialisation de DefAI sur device: {self.device}")
        
    def _get_device(self) -> str:
        """Détermine le device à utiliser"""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
            
    def load_model(self):
        """Charge le modèle et le tokenizer"""
        logger.info("Chargement du modèle DefAI...")
        
        try:
            # Charger le tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.base_model_path,
                trust_remote_code=True,
                padding_side="right"
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            # Charger le modèle de base
            base_model = AutoModelForCausalLM.from_pretrained(
                self.config.base_model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device,
                trust_remote_code=True
            )
            
            # Charger les poids fine-tunés
            self.model = PeftModel.from_pretrained(base_model, self.config.model_path)
            self.model.eval()
            
            # Créer le pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device
            )
            
            logger.info("Modèle DefAI chargé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle: {e}")
            raise
            
    def format_prompt(self, instruction: str) -> str:
        """Formate une instruction pour le modèle"""
        return f"### Instruction:\n{instruction}\n\n### Response:\n"
        
    def generate(self, instruction: str, **kwargs) -> Dict[str, Any]:
        """Génère une réponse pour une instruction"""
        try:
            # Paramètres par défaut
            generation_params = {
                "max_new_tokens": kwargs.get("max_new_tokens", self.config.max_new_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "top_k": kwargs.get("top_k", self.config.top_k),
                "do_sample": kwargs.get("do_sample", self.config.do_sample),
                "repetition_penalty": kwargs.get("repetition_penalty", self.config.repetition_penalty),
                "pad_token_id": self.tokenizer.eos_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
                "return_full_text": False
            }
            
            # Formater le prompt
            prompt = self.format_prompt(instruction)
            
            # Générer la réponse
            start_time = datetime.now()
            outputs = self.pipeline(prompt, **generation_params)
            end_time = datetime.now()
            
            response = outputs[0]['generated_text'].strip()
            generation_time = (end_time - start_time).total_seconds()
            
            return {
                "response": response,
                "generation_time": generation_time,
                "model": "DefAI (Gemma-2B fine-tuné)",
                "timestamp": end_time.isoformat(),
                "parameters": generation_params
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération: {e}")
            return {
                "error": str(e),
                "response": None,
                "generation_time": 0,
                "model": "DefAI",
                "timestamp": datetime.now().isoformat()
            }
            
    def health_check(self) -> Dict[str, Any]:
        """Vérifie l'état du modèle"""
        try:
            # Test simple
            test_response = self.generate("Test simple", max_new_tokens=10)
            
            return {
                "status": "healthy",
                "model": "DefAI (Gemma-2B fine-tuné)",
                "device": self.device,
                "test_response": test_response["response"][:50] + "..." if test_response["response"] else None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": "DefAI",
                "timestamp": datetime.now().isoformat()
            }


class DefAIInferenceAPI:
    """API Flask pour DefAI"""
    
    def __init__(self, config: InferenceConfig):
        self.config = config
        self.app = Flask(__name__)
        CORS(self.app)
        self.defai_model = None
        
        # Configuration
        self.app.config['JSON_AS_ASCII'] = False
        self.app.config['JSON_SORT_KEYS'] = False
        
        # Routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Configure les routes de l'API"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Vérifie l'état de l'API et du modèle"""
            if self.defai_model is None:
                return jsonify({
                    "status": "model_not_loaded",
                    "message": "Le modèle n'est pas encore chargé"
                }), 503
                
            return jsonify(self.defai_model.health_check())
            
        @self.app.route('/chat', methods=['POST'])
        def chat():
            """Endpoint principal pour le chat"""
            try:
                data = request.get_json()
                
                if not data or 'message' not in data:
                    return jsonify({
                        "error": "Le champ 'message' est requis"
                    }), 400
                    
                message = data['message']
                
                # Paramètres optionnels
                params = {}
                for param in ['max_new_tokens', 'temperature', 'top_p', 'top_k', 'do_sample', 'repetition_penalty']:
                    if param in data:
                        params[param] = data[param]
                        
                # Générer la réponse
                result = self.defai_model.generate(message, **params)
                
                if result.get("error"):
                    return jsonify(result), 500
                    
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Erreur dans /chat: {e}")
                return jsonify({
                    "error": str(e),
                    "response": None
                }), 500
                
        @self.app.route('/analyze', methods=['POST'])
        def analyze():
            """Analyse une situation ou un problème"""
            try:
                data = request.get_json()
                
                if not data or 'context' not in data:
                    return jsonify({
                        "error": "Le champ 'context' est requis"
                    }), 400
                    
                context = data['context']
                
                # Formater l'instruction pour l'analyse
                instruction = f"Analyse la situation suivante et fournis des recommandations pertinentes: {context}"
                
                result = self.defai_model.generate(instruction)
                
                if result.get("error"):
                    return jsonify(result), 500
                    
                return jsonify({
                    "context": context,
                    "analysis": result["response"],
                    "metadata": {
                        "generation_time": result["generation_time"],
                        "timestamp": result["timestamp"]
                    }
                })
                
            except Exception as e:
                logger.error(f"Erreur dans /analyze: {e}")
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/assist', methods=['POST'])
        def assist():
            """Assistance pour les utilisateurs"""
            try:
                data = request.get_json()
                
                if not data or 'query' not in data:
                    return jsonify({
                        "error": "Le champ 'query' est requis"
                    }), 400
                    
                query = data['query']
                user_role = data.get('user_role', 'user')
                
                # Formater l'instruction pour l'assistance
                instruction = f"En tant qu'assistant pour la plateforme universitaire, aide un {user_role} avec: {query}"
                
                result = self.defai_model.generate(instruction)
                
                if result.get("error"):
                    return jsonify(result), 500
                    
                return jsonify({
                    "query": query,
                    "user_role": user_role,
                    "assistance": result["response"],
                    "metadata": {
                        "generation_time": result["generation_time"],
                        "timestamp": result["timestamp"]
                    }
                })
                
            except Exception as e:
                logger.error(f"Erreur dans /assist: {e}")
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/routes/suggest', methods=['POST'])
        def suggest_routes():
            """Suggère des routes basées sur l'analyse"""
            try:
                data = request.get_json()
                
                if not data or 'user_activity' not in data:
                    return jsonify({
                        "error": "Le champ 'user_activity' est requis"
                    }), 400
                    
                activity = data['user_activity']
                
                instruction = f"Basé sur l'activité utilisateur suivante, suggère les routes pertinentes et des améliorations: {activity}"
                
                result = self.defai_model.generate(instruction)
                
                if result.get("error"):
                    return jsonify(result), 500
                    
                return jsonify({
                    "user_activity": activity,
                    "suggestions": result["response"],
                    "metadata": {
                        "generation_time": result["generation_time"],
                        "timestamp": result["timestamp"]
                    }
                })
                
            except Exception as e:
                logger.error(f"Erreur dans /routes/suggest: {e}")
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/debug/error', methods=['POST'])
        def debug_error():
            """Aide au débogage d'erreurs"""
            try:
                data = request.get_json()
                
                if not data or 'error_info' not in data:
                    return jsonify({
                        "error": "Le champ 'error_info' est requis"
                    }), 400
                    
                error_info = data['error_info']
                
                instruction = f"Aide à résoudre l'erreur suivante dans la plateforme universitaire: {error_info}"
                
                result = self.defai_model.generate(instruction)
                
                if result.get("error"):
                    return jsonify(result), 500
                    
                return jsonify({
                    "error_info": error_info,
                    "debug_help": result["response"],
                    "metadata": {
                        "generation_time": result["generation_time"],
                        "timestamp": result["timestamp"]
                    }
                })
                
            except Exception as e:
                logger.error(f"Erreur dans /debug/error: {e}")
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/info', methods=['GET'])
        def info():
            """Informations sur l'API et le modèle"""
            return jsonify({
                "api": "DefAI Inference API",
                "version": "1.0.0",
                "model": "Gemma-2B fine-tuné",
                "description": "API pour l'assistant IA DefAI de la plateforme universitaire",
                "endpoints": [
                    "/health - Vérification de l'état",
                    "/chat - Chat avec l'IA",
                    "/analyze - Analyse de situation",
                    "/assist - Assistance utilisateur",
                    "/routes/suggest - Suggestions de routes",
                    "/debug/error - Aide au débogage",
                    "/info - Informations sur l'API"
                ],
                "timestamp": datetime.now().isoformat()
            })
            
    def load_model(self):
        """Charge le modèle DefAI"""
        try:
            self.defai_model = DefAIModel(self.config)
            self.defai_model.load_model()
            logger.info("Modèle DefAI chargé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle: {e}")
            raise
            
    def run(self):
        """Démarre l'API"""
        logger.info(f"Démarrage de l'API DefAI sur {self.config.host}:{self.config.port}")
        
        # Charger le modèle avant de démarrer
        self.load_model()
        
        self.app.run(
            host=self.config.host,
            port=self.config.port,
            debug=self.config.debug
        )


def create_app(config_path: str = None) -> Flask:
    """Crée une application Flask (pour déploiement)"""
    config = InferenceConfig()
    
    if config_path and os.path.exists(config_path):
        # Charger la configuration depuis un fichier
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
            for key, value in config_dict.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    
    api = DefAIInferenceAPI(config)
    return api.app


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="API d'inférence DefAI")
    parser.add_argument("--host", default="0.0.0.0", help="Host de l'API")
    parser.add_argument("--port", type=int, default=5555, help="Port de l'API")
    parser.add_argument("--debug", action="store_true", help="Mode debug")
    parser.add_argument("--model-path", default="../model/gemma_finetuned", help="Path du modèle")
    parser.add_argument("--config", help="Fichier de configuration JSON")
    
    args = parser.parse_args()
    
    # Configuration
    config = InferenceConfig()
    config.host = args.host
    config.port = args.port
    config.debug = args.debug
    config.model_path = args.model_path
    
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config_dict = json.load(f)
            for key, value in config_dict.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    
    # Démarrer l'API
    api = DefAIInferenceAPI(config)
    api.run()
