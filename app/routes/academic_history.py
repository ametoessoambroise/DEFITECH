from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.models.academic import AcademicArchivedStudent
from app.models.user import User

academic_history_bp = Blueprint(
    "academic_history", __name__, url_prefix="/academic/history"
)


@academic_history_bp.route("/me")
@login_required
def my_history():
    """
    Vue Étudiant : Voir ses archives académiques.
    """
    if current_user.role != "etudiant":
        return redirect(url_for("main.index"))

    archives = AcademicArchivedStudent.query.filter_by(
        student_user_id=current_user.id
    ).all()
    return render_template("academic/history_student.html", archives=archives)


@academic_history_bp.route("/search")
@login_required
def search_history():
    """
    Vue Admin & Enseignant : Rechercher des archives.
    Admin : Tout voir.
    Enseignant : Voir (Filtrage à implémenter selon besoin, ici accès global lecture 'sa classe' simplifié).
    """
    if current_user.role not in ["admin", "enseignant"]:
        flash("Accès non autorisé.", "error")
        return redirect(url_for("main.index"))

    # Filtres
    nom = request.args.get("nom", "")
    filiere = request.args.get("filiere", "")
    annee = request.args.get("annee", "")

    query = AcademicArchivedStudent.query.join(
        User, AcademicArchivedStudent.student_user_id == User.id
    )

    if nom:
        query = query.filter(
            (User.nom.ilike(f"%{nom}%")) | (User.prenom.ilike(f"%{nom}%"))
        )

    if filiere:
        query = query.filter(AcademicArchivedStudent.filiere_nom.ilike(f"%{filiere}%"))

    if annee:
        query = query.filter(
            AcademicArchivedStudent.annee_academique.ilike(f"%{annee}%")
        )

    archives = (
        query.order_by(AcademicArchivedStudent.date_archivage.desc()).limit(50).all()
    )

    return render_template("academic/history_list.html", archives=archives)


@academic_history_bp.route("/view/<int:archive_id>")
@login_required
def view_archive(archive_id):
    """
    Détail d'une archive.
    """
    archive = AcademicArchivedStudent.query.get_or_404(archive_id)

    # Sécurité
    if current_user.role == "etudiant":
        if archive.student_user_id != current_user.id:
            abort(403)
    elif current_user.role not in ["admin", "enseignant"]:
        abort(403)

    return render_template("academic/history_detail.html", archive=archive)
