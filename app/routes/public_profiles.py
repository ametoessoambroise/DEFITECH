from flask import (
    Blueprint,
    render_template,
    abort,
    flash,
    redirect,
    url_for,
    request,
    jsonify,
)
from app.models.user import User
from app.models.formation import Formation
from app.models.experience import Experience
from app.models.projet import Projet
from app.models.competence import Competence
from app.models.langue import Langue
from flask_login import current_user

public_profile_bp = Blueprint("public_profile", __name__, url_prefix="/u")


@public_profile_bp.route("/")
def list_students():
    """
    Liste de tous les étudiants avec pagination.
    Accessible à tous (même sans connexion).
    """
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Récupérer tous les étudiants dont le profil est public
    students_query = User.query.filter_by(
        role="etudiant", is_public_profile=True
    ).order_by(User.nom, User.prenom)

    pagination = students_query.paginate(page=page, per_page=per_page, error_out=False)

    students = pagination.items

    if request.is_json or request.args.get("format") == "json":
        return jsonify(
            {
                "success": True,
                "data": {
                    "students": [
                        {
                            "id": s.id,
                            "nom": s.nom,
                            "prenom": s.prenom,
                            "photo": s.photo if s.photo else None,
                            "filiere": (
                                s.etudiant.filiere if hasattr(s, "etudiant") else None
                            ),
                            "annee": (
                                s.etudiant.annee if hasattr(s, "etudiant") else None
                            ),
                        }
                        for s in students
                    ],
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "current_page": pagination.page,
                },
            }
        )

    return render_template(
        "profile/students_directory.html", students=students, pagination=pagination
    )


@public_profile_bp.route("/<int:user_id>")
def view_profile(user_id):
    """
    Affichage du profil public d'un étudiant.
    Accessible à tous si le profil est public.
    """
    user = User.query.get_or_404(user_id)

    # Vérification du rôle (on se concentre sur les étudiants pour l'instant)
    if user.role != "etudiant":
        if request.is_json or request.args.get("format") == "json":
            return jsonify({"success": False, "error": "Profil non public"}), 403
        flash("Ce profil n'est pas accessible publiquement.", "warning")
        return redirect(url_for("main.index"))

    # Vérification de la visibilité
    is_owner = current_user.is_authenticated and current_user.id == user.id
    is_public = getattr(user, "is_public_profile", True)

    if not is_public and not is_owner:
        if request.is_json or request.args.get("format") == "json":
            return jsonify({"success": False, "error": "Profil privé"}), 404
        abort(404)

    etudiant = user.etudiant

    # Agrégation des données
    formations = (
        Formation.query.filter_by(user_id=user.id)
        .order_by(Formation.date_debut.desc())
        .all()
    )
    experiences = (
        Experience.query.filter_by(user_id=user.id)
        .order_by(Experience.date_debut.desc())
        .all()
    )
    projets = (
        Projet.query.filter_by(user_id=user.id).order_by(Projet.date_debut.desc()).all()
    )
    competences = Competence.query.filter_by(user_id=user.id).all()
    langues = Langue.query.filter_by(user_id=user.id).all()

    if request.is_json or request.args.get("format") == "json":
        return jsonify(
            {
                "success": True,
                "data": {
                    "user": {
                        "id": user.id,
                        "nom": user.nom,
                        "prenom": user.prenom,
                        "photo": user.photo if user.photo else None,
                        "bio": user.bio,
                        "filiere": etudiant.filiere if etudiant else None,
                        "annee": etudiant.annee if etudiant else None,
                    },
                    "competences": [
                        {"nom": c.nom, "niveau": c.niveau} for c in competences
                    ],
                    "formations": [
                        {"etablissement": f.etablissement, "diplome": f.diplome}
                        for f in formations
                    ],
                    "experiences": [
                        {"entreprise": ex.entreprise, "poste": ex.poste}
                        for ex in experiences
                    ],
                    "projets": [
                        {"titre": p.titre, "description": p.description}
                        for p in projets
                    ],
                    "langues": [
                        {"nom": lang.nom, "niveau": lang.niveau} for lang in langues
                    ],
                },
            }
        )

    return render_template(
        "profile/public_view.html",
        user=user,
        etudiant=etudiant,
        formations=formations,
        experiences=experiences,
        projets=projets,
        competences=competences,
        langues=langues,
        is_owner=is_owner,
    )
