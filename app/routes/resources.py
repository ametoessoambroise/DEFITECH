"""
Blueprint pour la gestion des ressources numériques

Fournit les routes pour :
- Lister les ressources
- Uploader de nouvelles ressources (enseignants uniquement)
- Rechercher des ressources
- Télécharger des ressources
- Supprimer des ressources
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    current_app,
    abort,
    jsonify,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_
import os
from datetime import datetime
import json
import mimetypes
from app.extensions import db

# Import des modèles
from app.models.resource import Resource
from app.models.matiere import Matiere
from app.models.enseignant import Enseignant
from app.models.etudiant import Etudiant
from app.models.filiere import Filiere

resources_bp = Blueprint("resources", __name__, url_prefix="/resources")

# Extensions de fichiers autorisées avec leurs catégories
ALLOWED_EXTENSIONS = {
    # Documents
    "pdf": "document",
    "doc": "document",
    "docx": "document",
    "odt": "document",
    "txt": "document",
    "html": "document",
    "css": "document",
    "js": "document",
    # Présentations
    "ppt": "presentation",
    "pptx": "presentation",
    "odp": "presentation",
    # Tableurs
    "xls": "spreadsheet",
    "xlsx": "spreadsheet",
    "ods": "spreadsheet",
    "csv": "spreadsheet",
    # Archives
    "zip": "archive",
    "rar": "archive",
    "7z": "archive",
    "tar": "archive",
    "gz": "archive",
    # Images
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "gif": "image",
    "svg": "image",
    "avif": "image",
    "webp": "image",
}

# Taille maximale des fichiers (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Types de ressources
RESOURCE_TYPES = [
    "livre",
    "cours",
    "td",
    "tp",
    "examen",
    "corrige",
    "support",
    "documentation",
    "autre",
]


def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_category(filename):
    """Retourne la catégorie du fichier"""
    if not filename or "." not in filename:
        return "unknown"
    ext = filename.rsplit(".", 1)[1].lower()
    return ALLOWED_EXTENSIONS.get(ext, "unknown")


def validate_file_size(file_storage):
    """Vérifie la taille du fichier"""
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    return size <= MAX_FILE_SIZE


def create_resource_folders():
    """Crée les dossiers nécessaires pour le stockage des ressources"""
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        raise ValueError("UPLOAD_FOLDER non configuré dans l'application")

    resources_folder = os.path.join(upload_folder, "resources")

    # Dossier principal
    os.makedirs(resources_folder, exist_ok=True)

    # Sous-dossiers par type de ressource
    for resource_type in RESOURCE_TYPES:
        os.makedirs(os.path.join(resources_folder, resource_type), exist_ok=True)

    # Dossier temporaire
    os.makedirs(os.path.join(resources_folder, "temp"), exist_ok=True)

    return resources_folder


def parse_json_or_csv(data):
    """Parse des données JSON ou CSV"""
    if not data:
        return []

    try:
        # Essayer d'abord JSON
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            return parsed.get("filieres", parsed.get("annees", []))
        elif isinstance(parsed, list):
            return parsed
        return []
    except (json.JSONDecodeError, TypeError, ValueError):
        # Si ce n'est pas du JSON, traiter comme CSV
        return [item.strip() for item in data.split(",") if item.strip()]


def get_enseignant_filieres(enseignant_id):
    """Récupère les filières et années enseignées par un enseignant"""
    enseignant = Enseignant.query.get(enseignant_id)
    if not enseignant:
        return [], []

    filieres = []
    annees = []

    if enseignant.filieres_enseignees:
        try:
            data = json.loads(enseignant.filieres_enseignees)
            if isinstance(data, dict):
                filieres = data.get("filieres", [])
                annees = data.get("annees", [])
            elif isinstance(data, list):
                filieres = data
        except (json.JSONDecodeError, TypeError, ValueError):
            # Si ce n'est pas du JSON, traiter comme CSV
            filieres = [
                item.strip()
                for item in enseignant.filieres_enseignees.split(",")
                if item.strip()
            ]

    return filieres, annees


def get_user_context():
    """Récupère le contexte utilisateur (profil, permissions, etc.)"""
    context = {
        "role": current_user.role,
        "user_id": current_user.id,
        "filieres": [],
        "annees": [],
        "matieres": [],
        "profile": None,
    }

    if current_user.role == "etudiant":
        etudiant = Etudiant.query.filter_by(user_id=current_user.id).first()

        if etudiant:
            context["profile"] = etudiant

            context["filieres"] = [etudiant.filiere]

            context["annees"] = [etudiant.annee]

            filiere_obj = Filiere.query.filter_by(nom=etudiant.filiere).first()
            filiere_id = filiere_obj.id if filiere_obj else None
            context["matieres"] = (
                Matiere.query.filter_by(filiere_id=filiere_id).all()
                if filiere_id
                else []
            )

    elif current_user.role == "enseignant":
        enseignant = Enseignant.query.filter_by(user_id=current_user.id).first()
        if enseignant:
            context["profile"] = enseignant
            filieres, annees = get_enseignant_filieres(enseignant.id)
            context["filieres"] = filieres
            context["annees"] = annees
            context["matieres"] = Matiere.query.filter_by(
                enseignant_id=enseignant.id
            ).all()

    elif current_user.role == "admin":
        context["filieres"] = [
            f[0] for f in db.session.query(Resource.filiere).distinct().all()
        ]
        context["annees"] = [
            a[0] for a in db.session.query(Resource.annee).distinct().all()
        ]
        context["matieres"] = Matiere.query.all()

    return context


def build_resources_query(user_context, filters):
    """Construit la requête pour récupérer les ressources selon le contexte"""
    query = Resource.query

    # Filtres selon le rôle
    if user_context["role"] == "etudiant" and user_context["profile"]:
        query = query.filter_by(
            filiere=user_context["profile"].filiere, annee=user_context["profile"].annee
        )
    elif user_context["role"] == "enseignant" and user_context["filieres"]:
        query = query.filter(Resource.filiere.in_(user_context["filieres"]))

    # Recherche textuelle
    search = filters.get("search", "").strip()
    if search:
        search_filter = or_(
            Resource.titre.ilike(f"%{search}%"),
            Resource.description.ilike(f"%{search}%"),
            Resource.nom_fichier.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    # Filtres spécifiques
    if filters.get("filiere"):
        query = query.filter_by(filiere=filters["filiere"])

    if filters.get("annee"):
        query = query.filter_by(annee=filters["annee"])

    if filters.get("type_ressource"):
        query = query.filter_by(type_ressource=filters["type_ressource"])

    if filters.get("matiere_id"):
        query = query.filter_by(matiere_id=filters["matiere_id"])

    return query.order_by(Resource.date_upload.desc())


def calculate_stats(resources):
    """Calcule les statistiques sur les ressources"""
    stats = {
        "total": len(resources),
        "pdfs": sum(1 for r in resources if r.type_fichier == "pdf"),
        "cours": sum(1 for r in resources if r.type_ressource == "cours"),
        "livres": sum(1 for r in resources if r.type_ressource == "livre"),
        "examens": sum(1 for r in resources if r.type_ressource == "examen"),
        "td": sum(1 for r in resources if r.type_ressource == "td"),
        "tp": sum(1 for r in resources if r.type_ressource == "tp"),
    }
    return stats


@resources_bp.route("/")
@login_required
def index():
    """
    Page principale des ressources numériques.

    Cette fonction est l'endpoint de la route '/' du blueprint 'resources_bp'.
    Elle est utilisée pour afficher la page principale des ressources numériques.

    Elle effectue les opérations suivantes :
    - Tente de se connecter à la base de données
    - Si une erreur se produit lors de la connexion à la base de données, affiche un message d'erreur et renvoie une page vide
    - Récupère le contexte utilisateur
    - Si le profil utilisateur n'est pas trouvé pour les utilisateurs qui ne sont pas les administrateurs, affiche un message d'erreur et renvoie une page vide
    - Récupère les filtres utilisés pour filtrer les ressources
    - Génère les statistiques sur les ressources filtrées
    - Renvoie la page principale des ressources numériques avec les ressources filtrées et les statistiques

    Retourne :
    - Une page HTML avec la liste des ressources filtrées et les statistiques

    """
    try:
        # Récupérer le contexte utilisateur
        user_context = get_user_context()

        if not user_context["profile"] and user_context["role"] != "admin":
            flash(
                "Profil utilisateur non trouvé. Veuillez contacter l'administrateur.",
                "error",
            )
            return render_template("resources/index.html", resources=[], stats={})

        # Récupérer les filtres
        filters = {
            "search": request.args.get("search", "").strip(),
            "filiere": request.args.get("filiere", ""),
            "annee": request.args.get("annee", ""),
            "type_ressource": request.args.get("type_ressource", ""),
            "matiere_id": request.args.get("matiere_id", type=int),
        }

        # Construire la requête et récupérer les ressources
        query = build_resources_query(user_context, filters)
        resources = query.all()

        # Calculer les statistiques
        stats = calculate_stats(resources)

        return render_template(
            "resources/index.html",
            resources=resources,
            filieres=user_context["filieres"],
            annees=user_context["annees"],
            matieres=user_context["matieres"],
            resource_types=RESOURCE_TYPES,
            selected_filiere=filters["filiere"],
            selected_annee=filters["annee"],
            selected_type=filters["type_ressource"],
            selected_matiere=filters["matiere_id"],
            search=filters["search"],
            stats=stats,
        )

    except Exception as e:
        current_app.logger.error(f"Erreur dans resources.index: {str(e)}")
        flash("Une erreur est survenue lors du chargement des ressources.", "error")
        return render_template("resources/index.html", resources=[], stats={})


@resources_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """
    Upload d'une nouvelle ressource (enseignants uniquement).

    Cette fonction est l'endpoint de la route '/upload' du blueprint 'resources_bp'.
    Elle est utilisée pour permettre aux enseignants de téléverser de nouvelles ressources.

    Elle effectue les opérations suivantes :
    - Vérifie si l'utilisateur est un enseignant. Si ce n'est pas le cas, affiche un message d'erreur et redirige vers la page d'accueil.

    Retourne :
    - Si l'utilisateur n'est pas un enseignant, redirige vers la page d'accueil avec un message d'erreur.

    """
    if current_user.role != "enseignant":
        flash("Seuls les enseignants peuvent uploader des ressources.", "error")
        return redirect(url_for("resources.index"))

    enseignant = Enseignant.query.filter_by(user_id=current_user.id).first()
    if not enseignant:
        flash("Profil enseignant non trouvé.", "error")
        return redirect(url_for("resources.index"))

    filieres, annees = get_enseignant_filieres(enseignant.id)
    matieres = Matiere.query.filter_by(enseignant_id=enseignant.id).all()

    if not filieres or not annees:
        flash(
            "Aucune filière ou année assignée. Veuillez contacter l'administrateur.",
            "warning",
        )

    if request.method == "POST":
        # Validation des champs
        titre = request.form.get("titre", "").strip()
        description = request.form.get("description", "").strip()
        type_ressource = request.form.get("type_ressource", "")
        filiere = request.form.get("filiere", "")
        annee = request.form.get("annee", "")
        matiere_id = request.form.get("matiere_id", type=int)

        # Validation des données
        errors = []

        if not titre:
            errors.append("Le titre est obligatoire.")
        elif len(titre) > 200:
            errors.append("Le titre ne doit pas dépasser 200 caractères.")

        if not type_ressource or type_ressource not in RESOURCE_TYPES:
            errors.append("Type de ressource invalide.")

        if not filiere or filiere not in filieres:
            errors.append("Filière invalide ou non autorisée.")

        if not annee or annee not in annees:
            errors.append("Année invalide ou non autorisée.")

        if description and len(description) > 1000:
            errors.append("La description ne doit pas dépasser 1000 caractères.")

        # Validation du fichier
        if "fichier" not in request.files:
            errors.append("Aucun fichier sélectionné.")
        else:
            fichier = request.files["fichier"]
            if fichier.filename == "":
                errors.append("Aucun fichier sélectionné.")
            elif not allowed_file(fichier.filename):
                errors.append(
                    f"Type de fichier non autorisé. Extensions acceptées: {', '.join(sorted(ALLOWED_EXTENSIONS.keys()))}"
                )
            elif not validate_file_size(fichier):
                errors.append(
                    f"Le fichier est trop volumineux. Taille maximale: {MAX_FILE_SIZE // (1024 * 1024)} MB"
                )

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(request.url)

        fichier = request.files["fichier"]

        try:
            # Créer les dossiers si nécessaire
            resources_folder = create_resource_folders()
            resource_type_folder = os.path.join(resources_folder, type_ressource)
            os.makedirs(resource_type_folder, exist_ok=True)

            # Générer un nom de fichier unique et sécurisé
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = secure_filename(fichier.filename)
            name, ext = os.path.splitext(filename)

            # Limiter la longueur du nom
            if len(name) > 100:
                name = name[:100]

            unique_filename = f"{timestamp}_{name}{ext}"
            filepath = os.path.join(resource_type_folder, unique_filename)

            # Sauvegarder le fichier
            fichier.save(filepath)
            file_size = os.path.getsize(filepath)

            # Chemin relatif pour la base de données
            relative_path = os.path.join("uploads", type_ressource, unique_filename)
            relative_path = relative_path.replace("\\", "/")

            # Créer l'enregistrement dans la base de données
            resource = Resource(
                titre=titre,
                description=description,
                nom_fichier=filename,
                chemin_fichier=relative_path,
                type_fichier=ext[1:].lower(),  # Extension sans le point
                taille=file_size,
                type_ressource=type_ressource,
                filiere=filiere,
                annee=annee,
                matiere_id=matiere_id if matiere_id else None,
                enseignant_id=current_user.id,
            )

            db.session.add(resource)
            db.session.commit()

            flash(f"Ressource '{titre}' uploadée avec succès !", "success")
            current_app.logger.info(
                f"Ressource uploadée: {titre} par {current_user.prenom} {current_user.nom} ({current_user.email})"
            )
            return redirect(url_for("resources.index"))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur lors de l'upload: {str(e)}")

            # Supprimer le fichier si la transaction échoue
            if "filepath" in locals() and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

            flash(f"Erreur lors de l'upload : {str(e)}", "error")
            return redirect(request.url)

    return render_template(
        "resources/upload.html",
        filieres=filieres,
        annees=annees,
        matieres=matieres,
        resource_types=RESOURCE_TYPES,
        allowed_extensions=sorted(ALLOWED_EXTENSIONS.keys()),
        max_file_size_mb=MAX_FILE_SIZE // (1024 * 1024),
    )


@resources_bp.route("/download/<int:resource_id>")
@login_required
def download(resource_id):
    """
    Télécharge une ressource.

    Cette fonction est l'endpoint de la route '/download/<int:resource_id>' du blueprint 'resources_bp'.
    Elle est utilisée pour télécharger une ressource en utilisant son identifiant unique.

    Args:
        resource_id (int): Identifiant unique de la ressource.

    Retourne:
        Une réponse HTTP contenant le fichier à télécharger.

    """
    resource = Resource.query.get_or_404(resource_id)

    # Vérifier les permissions d'accès
    has_access = False

    if current_user.role == "admin":
        has_access = True

    elif current_user.role == "etudiant":
        etudiant = Etudiant.query.filter_by(user_id=current_user.id).first()
        if (
            etudiant
            and etudiant.filiere == resource.filiere
            and etudiant.annee == resource.annee
        ):
            has_access = True

    elif current_user.role == "enseignant":
        filieres, _ = get_enseignant_filieres(current_user.id)
        if resource.filiere in filieres:
            has_access = True

    if not has_access:
        current_app.logger.warning(
            f"Tentative d'accès non autorisé à la ressource {resource_id} par {current_user.prenom} {current_user.nom} ({current_user.email})"
        )
        abort(403, "Vous n'avez pas l'autorisation d'accéder à cette ressource.")

    # Construire le chemin complet
    chemin_fichier = resource.chemin_fichier
    # Si le chemin commence par "uploads/", on le supprime pour éviter la duplication
    if chemin_fichier.startswith("uploads/"):
        chemin_fichier = chemin_fichier[8:]  # Enlève "uploads/"

    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], chemin_fichier)
    # Vérifier l'existence du fichier
    if not os.path.exists(full_path):
        current_app.logger.error(f"Fichier introuvable: {full_path}")
        flash("Le fichier demandé n'existe plus.", "error")
        return redirect(url_for("resources.index"))

    try:
        # Incrémenter le compteur de téléchargements si disponible
        if hasattr(resource, "nombre_telechargements"):
            resource.nombre_telechargements += 1
            db.session.commit()

        # Déterminer le type MIME
        mime_type = mimetypes.guess_type(resource.nom_fichier)[0]

        return send_from_directory(
            os.path.dirname(full_path),
            os.path.basename(full_path),
            as_attachment=True,
            download_name=resource.nom_fichier,
            mimetype=mime_type,
        )

    except Exception as e:
        current_app.logger.error(f"Erreur lors du téléchargement: {str(e)}")
        flash("Erreur lors du téléchargement du fichier.", "error")
        return redirect(url_for("resources.index"))


@resources_bp.route("/delete/<int:resource_id>", methods=["POST"])
@login_required
def delete(resource_id):
    """
    Supprime une ressource.

    Cette fonction est l'endpoint de la route '/delete/<int:resource_id>' du blueprint 'resources_bp'.
    Elle est utilisée pour supprimer une ressource en utilisant son identifiant unique.

    Seuls les enseignants et les administrateurs peuvent supprimer des ressources.

    Args:
        resource_id (int): Identifiant unique de la ressource.

    Retourne:
        Une redirection vers la page d'accueil des ressources si la suppression est réussie.
        Une redirection vers la page d'accueil des ressources avec un message d'erreur si l'utilisateur n'a pas l'autorisation de supprimer des ressources.
        Une redirection vers la page d'accueil des ressources avec un message d'erreur si l'utilisateur ne peut pas supprimer la ressource en question.

    """
    if current_user.role not in ["enseignant", "admin"]:
        flash("Vous n'avez pas l'autorisation de supprimer des ressources.", "error")
        return redirect(url_for("resources.index"))

    resource = Resource.query.get_or_404(resource_id)

    # Vérifier que l'utilisateur est l'auteur de la ressource ou admin
    if resource.enseignant_id != current_user.id and current_user.role != "admin":
        flash("Vous ne pouvez supprimer que vos propres ressources.", "error")
        return redirect(url_for("resources.index"))

    try:
        # Supprimer le fichier physique
        if hasattr(resource, "delete_file"):
            resource.delete_file()
        else:
            # Fallback si la méthode n'existe pas
            full_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], resource.chemin_fichier
            )
            if os.path.exists(full_path):
                os.remove(full_path)

        # Supprimer l'enregistrement de la base de données
        titre = resource.titre
        db.session.delete(resource)
        db.session.commit()

        current_app.logger.info(
            f"Ressource supprimée: {titre} par {current_user.prenom} {current_user.nom} ({current_user.email})"
        )
        flash(f"Ressource '{titre}' supprimée avec succès.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur lors de la suppression: {str(e)}")
        flash(f"Erreur lors de la suppression : {str(e)}", "error")

    return redirect(url_for("resources.index"))


@resources_bp.route("/my-resources")
@login_required
def my_resources():
    """
    Affiche les ressources téléchargées par l'utilisateur connecté.

    Cette fonction est l'endpoint de la route '/my-resources' du blueprint 'resources_bp'.
    Elle est utilisée pour afficher les ressources téléchargées par l'utilisateur connecté.

    Retourne :
    - Une page HTML avec la liste des ressources téléchargées par l'utilisateur connecté.

    """
    if current_user.role != "enseignant":
        flash("Seuls les enseignants peuvent voir leurs ressources.", "error")
        return redirect(url_for("resources.index"))

    try:
        resources = (
            Resource.query.filter_by(enseignant_id=current_user.id)
            .order_by(Resource.date_upload.desc())
            .all()
        )

        stats = calculate_stats(resources)

        return render_template(
            "resources/my_resources.html",
            resources=resources,
            stats=stats,
        )

    except Exception as e:
        current_app.logger.error(f"Erreur dans my_resources: {str(e)}")
        flash("Erreur lors du chargement de vos ressources.", "error")
        return redirect(url_for("resources.index"))


@resources_bp.route("/api/stats")
@login_required
def api_stats():
    """
    API pour récupérer les statistiques.

    Cette fonction est l'endpoint de la route '/api/stats' du blueprint 'resources_bp'.
    Elle est utilisée pour récupérer les statistiques sur les ressources.

    Retourne:
        - Un JSON contenant une clé 'success' à True si la requête a réussi,
          et une clé 'stats' contenant les statistiques sur les ressources.
        - Ou un JSON contenant une clé 'success' à False et une clé 'error'
          contenant une description de l'erreur si une erreur s'est produite.

    """
    try:
        user_context = get_user_context()
        query = build_resources_query(user_context, {})
        resources = query.all()
        stats = calculate_stats(resources)

        return jsonify({"success": True, "stats": stats})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@resources_bp.errorhandler(413)
def request_entity_too_large(error):
    """
    Gestion de l'erreur lorsque le fichier est trop volumineux.

    Cette fonction est appelée lorsque la taille du fichier envoyé dépassé la limite autorisée.

    Args:
        error (Exception): L'exception de type werkzeug.exceptions.RequestEntityTooLarge

    Retourne:
        Une redirection vers la page d'upload avec un message d'erreur.

    """
    flash(
        f"Le fichier est trop volumineux. Taille maximale: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        "error",
    )
    return redirect(url_for("resources.upload"))
