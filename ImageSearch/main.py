from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import requests
import os
import json
import io
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional, List

# Configuration
UNSPLASH_ACCESS_KEY = "tiPGSSsgw9JBOq3x-dxdjpUKpApceJ7xqjHcua9bGGY"
UNSPLASH_API_URL = "https://api.unsplash.com"
DATA_DIR = "data/images"
METADATA_FILE = "data/metadata.json"

# Créer les dossiers nécessaires
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# Base de données
DATABASE_URL = "sqlite:///./data/seeker_ai.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Modèles de base de données
class SearchQuery(Base):
    __tablename__ = "search_queries"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, index=True)
    results_count = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)


class GeneratedImage(Base):
    __tablename__ = "generated_images"
    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text)
    style = Column(String)
    image_path = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


# Créer les tables
Base.metadata.create_all(bind=engine)


# Modèles Pydantic
class GenerateRequest(BaseModel):
    prompt: str
    style: Optional[str] = "realistic"


class ImageResponse(BaseModel):
    id: str
    url: str
    description: Optional[str] = None
    likes: Optional[int] = 0
    query: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class SearchResponse(BaseModel):
    query: str
    images: List[ImageResponse]
    total: int


# Application FastAPI
app = FastAPI(
    title="Seeker AI Backend",
    description="API pour la recherche et génération d'images par IA",
    version="1.0.0",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dépendance pour la session DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Routes de l'API


@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "Bienvenue sur Seeker AI API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/search",
            "generate": "/api/generate",
            "train": "/api/train",
            "stats": "/api/stats",
        },
    }


@app.get("/api/search", response_model=SearchResponse)
async def search_images(
    query: str,
    per_page: int = 12,
    page: int = 1,
    type: Optional[str] = None,
    color: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Rechercher des images via l'API Unsplash

    Args:
        query: Terme de recherche
        per_page: Nombre d'images par page (max 30)
        page: Numéro de page
        type: Type d'image (photos, illustrations, art)
        color: Filtre de couleur
    """
    try:
        # Construire l'URL de l'API Unsplash
        url = f"{UNSPLASH_API_URL}/search/photos"
        headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
            "Accept-Version": "v1",
        }

        # Préparer les paramètres
        params = {
            "query": query,
            "per_page": min(per_page, 30),  # Limite Unsplash
            "page": page,
        }

        # Ajouter les filtres optionnels
        if type == "illustrations":
            params["orientation"] = "portrait"
        elif type == "art":
            params["query"] = f"{query} digital art"

        if color:
            params["color"] = color

        # Faire la requête à Unsplash
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Traiter les résultats
        images_data = []
        for result in data.get("results", []):
            image_info = ImageResponse(
                id=result["id"],
                url=result["urls"]["regular"],
                description=result.get("description") or result.get("alt_description"),
                likes=result.get("likes", 0),
                query=query,
                width=result.get("width"),
                height=result.get("height"),
            )
            images_data.append(image_info)

            # Sauvegarder localement
            try:
                image_filename = f"{query.replace(' ', '_')}_{result['id']}.jpg"
                image_path = os.path.join(DATA_DIR, image_filename)

                # Télécharger l'image si elle n'existe pas
                if not os.path.exists(image_path):
                    img_response = requests.get(result["urls"]["regular"], timeout=10)
                    if img_response.status_code == 200:
                        with open(image_path, "wb") as f:
                            f.write(img_response.content)
            except Exception as e:
                print(f"Erreur lors de la sauvegarde de l'image {result['id']}: {e}")

        # Sauvegarder les métadonnées
        save_metadata(query, images_data)

        # Enregistrer la recherche dans la DB
        search_entry = SearchQuery(query=query, results_count=len(images_data))
        db.add(search_entry)
        db.commit()

        return SearchResponse(query=query, images=images_data, total=len(images_data))

    except requests.RequestException as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur lors de la recherche Unsplash: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/api/generate")
async def generate_image(request: GenerateRequest, db: Session = Depends(get_db)):
    """
    Générer une image basée sur un prompt

    Note: Cette version utilise une image de démonstration.
    Dans une version de production, vous intégreriez un modèle de génération d'images
    comme Stable Diffusion, DALL-E, ou Midjourney.
    """
    try:
        # Pour la démonstration, utiliser une image existante ou générer une image placeholder
        # Dans une vraie application, vous appelleriez votre modèle de génération d'images ici

        # Option 1: Utiliser une image existante du stockage
        if os.path.exists(DATA_DIR) and os.listdir(DATA_DIR):
            images = [
                f for f in os.listdir(DATA_DIR) if f.endswith((".jpg", ".png", ".jpeg"))
            ]
            if images:
                selected_image = images[0]
                image_path = os.path.join(DATA_DIR, selected_image)

                # Enregistrer dans la DB
                gen_entry = GeneratedImage(
                    prompt=request.prompt, style=request.style, image_path=image_path
                )
                db.add(gen_entry)
                db.commit()

                return FileResponse(
                    image_path,
                    media_type="image/jpeg",
                    headers={
                        "Content-Disposition": f"attachment; filename=generated_{gen_entry.id}.jpg"
                    },
                )

        # Option 2: Utiliser une image placeholder de Lorem Picsum
        placeholder_url = (
            f"https://picsum.photos/600/400?random={hash(request.prompt) % 10000}"
        )
        response = requests.get(placeholder_url, timeout=10)

        if response.status_code == 200:
            # Sauvegarder l'image générée
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"generated_{timestamp}.jpg"
            image_path = os.path.join(DATA_DIR, image_filename)

            with open(image_path, "wb") as f:
                f.write(response.content)

            # Enregistrer dans la DB
            gen_entry = GeneratedImage(
                prompt=request.prompt, style=request.style, image_path=image_path
            )
            db.add(gen_entry)
            db.commit()

            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="image/jpeg",
                headers={
                    "Content-Disposition": f"attachment; filename={image_filename}"
                },
            )

        raise HTTPException(status_code=500, detail="Impossible de générer l'image")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur lors de la génération: {str(e)}"
        )


@app.post("/api/train")
async def train_model(db: Session = Depends(get_db)):
    """
    Entraîner le modèle d'IA avec les données collectées

    Note: Cette route déclenche l'entraînement du modèle en arrière-plan.
    Dans une vraie application, vous utiliseriez Celery ou un système de queue.
    """
    try:
        # Vérifier qu'il y a des données
        if not os.path.exists(METADATA_FILE):
            raise HTTPException(
                status_code=404, detail="Aucune donnée disponible pour l'entraînement"
            )

        with open(METADATA_FILE, "r") as f:
            metadata_list = json.load(f)

        if not metadata_list:
            raise HTTPException(
                status_code=404, detail="Aucune donnée disponible pour l'entraînement"
            )

        # Compter le nombre d'images disponibles
        total_images = sum(len(m.get("results", [])) for m in metadata_list)

        # Dans une vraie application, vous lanceriez l'entraînement ici
        # import subprocess
        # subprocess.Popen(['python', 'train_model.py'])

        return {
            "message": "Entraînement du modèle démarré",
            "total_searches": len(metadata_list),
            "total_images": total_images,
            "status": "processing",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du lancement de l'entraînement: {str(e)}",
        )


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Obtenir des statistiques sur l'utilisation de l'application"""
    try:
        # Compter les recherches
        total_searches = db.query(SearchQuery).count()

        # Compter les images générées
        total_generated = db.query(GeneratedImage).count()

        # Recherches récentes
        recent_searches = (
            db.query(SearchQuery).order_by(SearchQuery.timestamp.desc()).limit(10).all()
        )

        # Termes les plus recherchés
        from sqlalchemy import func

        popular_queries = (
            db.query(SearchQuery.query, func.count(SearchQuery.query).label("count"))
            .group_by(SearchQuery.query)
            .order_by(func.count(SearchQuery.query).desc())
            .limit(10)
            .all()
        )

        return {
            "total_searches": total_searches,
            "total_generated": total_generated,
            "recent_searches": [
                {
                    "query": s.query,
                    "results_count": s.results_count,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in recent_searches
            ],
            "popular_queries": [{"query": q, "count": c} for q, c in popular_queries],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}",
        )


# Fonctions utilitaires


def save_metadata(query: str, images: List[ImageResponse]):
    """Sauvegarder les métadonnées des recherches"""
    try:
        metadata = {
            "query": query,
            "results": [img.dict() for img in images],
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Charger les métadonnées existantes
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, "r") as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        # Ajouter les nouvelles métadonnées
        existing_data.append(metadata)

        # Limiter à 1000 entrées pour éviter un fichier trop volumineux
        if len(existing_data) > 1000:
            existing_data = existing_data[-1000:]

        # Sauvegarder
        with open(METADATA_FILE, "w") as f:
            json.dump(existing_data, f, indent=2)

    except Exception as e:
        print(f"Erreur lors de la sauvegarde des métadonnées: {e}")


# Point d'entrée pour exécuter l'application
# if __name__ == "__main__":
#     import uvicorn

#     print("🚀 Démarrage de Seeker AI Backend...")
#     print("📍 API disponible sur: http://localhost:8000")
#     print("📖 Documentation: http://localhost:8000/docs")
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
