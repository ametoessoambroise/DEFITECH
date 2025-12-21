from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
import json
import io
import pandas as pd
import random

from app.extensions import db
from app.models.user import User
from app.models.etudiant import Etudiant
from app.models.enseignant import Enseignant
from app.models.filiere import Filiere
from app.models.annee import Annee
from app.models.matiere import Matiere
from app.models.notification import Notification
from app.models.note import Note

# Conditional imports for models that might not rely on app context immediately
# but better to import them at top level if possible, or inside functions if circular deps strictly needed.
# For now, top level is fine as models should be standalone.
try:
    from app.models.teacher_profile_update_request import TeacherProfileUpdateRequest
except ImportError:
    TeacherProfileUpdateRequest = None

from app.email_utils import send_account_validation_email

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Page d'administration du tableau de bord.
    """

    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("main.index"))

    users_en_attente = User.query.filter_by(statut="en_attente").count()
    total_etudiants = User.query.filter_by(role="etudiant", statut="approuve").count()
    total_enseignants = User.query.filter_by(
        role="enseignant", statut="approuve"
    ).count()
    total_filieres = Filiere.query.count()

    # Notifications récentes pour l'admin
    notifications_admin = (
        Notification.query.order_by(Notification.date_created.desc()).limit(5).all()
    )

    # Demandes de modification de profil des enseignants en attente
    pending_teacher_requests = 0
    if TeacherProfileUpdateRequest:
        try:
            pending_teacher_requests = TeacherProfileUpdateRequest.query.filter_by(
                statut="en_attente"
            ).count()
        except Exception:
            pending_teacher_requests = 0

    return render_template(
        "admin/dashboard.html",
        users_en_attente=users_en_attente,
        total_etudiants=total_etudiants,
        total_enseignants=total_enseignants,
        total_filieres=total_filieres,
        notifications_admin=notifications_admin,
        pending_teacher_requests=pending_teacher_requests,
    )


@admin_bp.route("/users")
@login_required
def users():
    """
    Page d'administration des utilisateurs.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("main.index"))

    # Filtrer les utilisateurs par statut si spécifié
    statut = request.args.get("statut")
    if statut:
        users = User.query.filter_by(statut=statut).all()
    else:
        users = User.query.all()

    # Compter les utilisateurs par statut pour les statistiques
    users_en_attente = User.query.filter_by(statut="en_attente").count()
    users_approuves = User.query.filter_by(statut="approuve").count()
    users_rejetes = User.query.filter_by(statut="rejete").count()
    total_users = users_en_attente + users_approuves + users_rejetes

    # Préparer les dictionnaires pour accès rapide dans le template
    etudiants = Etudiant.query.all()
    enseignants = Enseignant.query.all()
    etudiants_dict = {e.user_id: e for e in etudiants}
    enseignants_dict = {e.user_id: e for e in enseignants}

    return render_template(
        "admin/users.html",
        users=users,
        etudiants_dict=etudiants_dict,
        enseignants_dict=enseignants_dict,
        statut_courant=statut,
        users_en_attente=users_en_attente,
        users_approuves=users_approuves,
        users_rejetes=users_rejetes,
        total_users=total_users,
    )


@admin_bp.route("/approve/<int:user_id>")
@login_required
def approve_user(user_id):
    """
    Fonction pour approuver un utilisateur.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("main.index"))

    user = User.query.get_or_404(user_id)
    user.statut = "approuve"
    db.session.commit()

    # Envoyer un email de validation du compte
    send_account_validation_email(user)

    # Ajouter une notification interne pour l'utilisateur validé
    notif = Notification(
        user_id=user.id,
        message="Votre compte a été validé par l'administration.",
        type="success",
    )
    db.session.add(notif)
    db.session.commit()

    # Si l'utilisateur est un étudiant, créer son profil
    if user.role == "etudiant":
        etudiant_exists = Etudiant.query.filter_by(user_id=user.id).first()
        if not etudiant_exists:
            # Générer un numéro d'étudiant unique
            while True:
                new_numero = f"ETU{datetime.now().year}{random.randint(10000, 99999)}"
                if not Etudiant.query.filter_by(numero_etudiant=new_numero).first():
                    break

            etudiant = Etudiant(
                user_id=user.id,
                filiere=user.filiere if hasattr(user, "filiere") else "Informatique",
                annee=user.annee if hasattr(user, "annee") else "1ère année",
                numero_etudiant=new_numero,
            )
            db.session.add(etudiant)
            db.session.commit()
            flash(f"Profil étudiant pour {user.nom} {user.prenom} créé.", "success")
        else:
            flash(f"L'étudiant {user.nom} {user.prenom} a déjà un profil.", "info")
    elif user.role == "enseignant":
        enseignant_exists = Enseignant.query.filter_by(user_id=user.id).first()
        if not enseignant_exists:
            enseignant = Enseignant(
                user_id=user.id,
                specialite="",
                filieres_enseignees=json.dumps({"filieres": [], "annees": []}),
            )
            db.session.add(enseignant)
            db.session.commit()
            flash(f"Profil enseignant pour {user.nom} {user.prenom} créé.", "success")
        else:
            flash(
                f"L'enseignant {user.nom} {user.prenom} a déjà un profil.",
                "info",
            )

    flash(
        f"L'utilisateur {user.nom} {user.prenom} a été approuvé avec succès.", "success"
    )
    return redirect(url_for("admin.users"))


@admin_bp.route("/reject/<int:user_id>")
@login_required
def reject_user(user_id):
    """
    Fonction pour rejeter un utilisateur.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("main.index"))

    user = User.query.get_or_404(user_id)
    if user.statut == "rejete":
        flash("Cet utilisateur a déjà été rejeté.", "warning")
        return redirect(url_for("admin.users"))

    user.statut = "rejete"
    db.session.commit()

    # Ajouter une notification interne pour l'utilisateur rejeté
    notif = Notification(
        user_id=user.id,
        message="Votre compte a été rejeté par l'administration. Veuillez contacter le support pour plus d'informations.",
        type="error",
    )
    db.session.add(notif)
    db.session.commit()

    flash(f"L'utilisateur {user.nom} {user.prenom} a été rejeté.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/delete/<int:user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id):
    """
    Fonction pour supprimer un utilisateur.
    """
    if current_user.role != "admin":
        return jsonify({"success": False, "message": "Accès non autorisé"}), 403

    user = db.session.get(
        User, user_id
    )  # Utilisation de la nouvelle syntaxe SQLAlchemy 2.0
    if not user:
        return jsonify({"success": False, "message": "Utilisateur non trouvé"}), 404

    try:
        # Utiliser l'approche SQL brute pour les tables problématiques
        with db.session.begin_nested():
            with db.session.no_autoflush:
                # Imports inside to avoid circular or early import issues if models are tricky
                from app.models.message import Message
                from app.models.study_document import StudyDocument
                from app.models.study_progress import StudyProgress
                from app.models.study_session import StudySession
                from app.models.quiz_models import Quiz, QuizAttempt, QuizAnswer
                from app.models.flashcard import Flashcard, FlashcardReview
                from app.models.suggestion import Suggestion, SuggestionVote
                from app.models.password_reset_token import PasswordResetToken
                from app.models.competence import Competence
                from app.models.experience import Experience
                from app.models.formation import Formation
                from app.models.langue import Langue
                from app.models.projet import Projet
                from app.models.videoconference import (
                    RoomParticipant,
                    RoomActivityLog,
                    Inscription,
                    RoomInvitation,
                    Room,
                )
                from app.models.resource import Resource
                from app.models.global_notification import GlobalNotification
                from app.models.pomodoro_session import PomodoroSession
                from app.models.devoir import Devoir
                from app.models.devoir_vu import DevoirVu
                from app.models.presence import Presence
                from app.models.emploi_temps import EmploiTemps

                # 1. Supprimer les messages avec approche SQL brute
                try:
                    db.session.execute(
                        db.text("DELETE FROM message WHERE sender_id = :user_id"),
                        {"user_id": user_id},
                    )
                    db.session.execute(
                        db.text("DELETE FROM message WHERE receiver_id = :user_id"),
                        {"user_id": user_id},
                    )
                except Exception as e:
                    current_app.logger.error(
                        f"Erreur lors de la suppression des messages: {str(e)}"
                    )
                    # Fallback SQLAlchemy
                    Message.query.filter_by(sender_id=user_id).delete()
                    Message.query.filter_by(receiver_id=user_id).delete()

                # 2. Supprimer les study_documents avec approche SQL brute
                try:
                    db.session.execute(
                        db.text("DELETE FROM study_documents WHERE user_id = :user_id"),
                        {"user_id": user_id},
                    )
                except Exception as e:
                    current_app.logger.error(
                        f"Erreur lors de la suppression des study_documents: {str(e)}"
                    )
                    StudyDocument.query.filter_by(user_id=user_id).delete()

                # 3. Supprimer les autres tables user_id
                # Progression et sessions
                StudyProgress.query.filter_by(user_id=user_id).delete()
                StudySession.query.filter_by(user_id=user_id).delete()

                # Compétences, expériences, formations, langues, projets
                Competence.query.filter_by(user_id=user_id).delete()
                Experience.query.filter_by(user_id=user_id).delete()
                Formation.query.filter_by(user_id=user_id).delete()
                Langue.query.filter_by(user_id=user_id).delete()
                Projet.query.filter_by(user_id=user_id).delete()

                # Vidéoconférence
                RoomInvitation.query.filter_by(user_id=user_id).delete()
                rooms_hotees = Room.query.filter_by(host_id=user_id).all()
                for room in rooms_hotees:
                    RoomInvitation.query.filter_by(room_id=room.id).delete()
                RoomParticipant.query.filter_by(user_id=user_id).delete()
                RoomActivityLog.query.filter_by(user_id=user_id).delete()
                Inscription.query.filter_by(user_id=user_id).delete()
                Room.query.filter_by(host_id=user_id).delete()

                # Ressources et notifications globales
                Resource.query.filter_by(enseignant_id=user_id).delete()
                GlobalNotification.query.filter_by(createur_id=user_id).delete()

                # Quiz, flashcards, suggestions, tokens
                Quiz.query.filter_by(user_id=user_id).delete()
                QuizAttempt.query.filter_by(user_id=user_id).delete()
                QuizAnswer.query.filter_by(user_id=user_id).delete()
                Flashcard.query.filter_by(user_id=user_id).delete()
                FlashcardReview.query.filter_by(user_id=user_id).delete()
                Suggestion.query.filter_by(user_id=user_id).delete()
                SuggestionVote.query.filter_by(user_id=user_id).delete()
                PasswordResetToken.query.filter_by(user_id=user_id).delete()
                if TeacherProfileUpdateRequest:
                    TeacherProfileUpdateRequest.query.filter_by(
                        user_id=user_id
                    ).delete()

                # 4. Supprimer les entités dépendantes
                # Étudiants
                etudiants = Etudiant.query.filter_by(user_id=user_id).all()
                for etudiant in etudiants:
                    Presence.query.filter_by(etudiant_id=etudiant.id).delete()
                    Note.query.filter_by(etudiant_id=etudiant.id).delete()
                    PomodoroSession.query.filter_by(etudiant_id=etudiant.id).delete()
                    db.session.delete(etudiant)

                # Enseignants
                enseignants = Enseignant.query.filter_by(user_id=user_id).all()
                for enseignant in enseignants:
                    EmploiTemps.query.filter_by(enseignant_id=enseignant.id).delete()

                    # Supprimer les devoirs
                    try:
                        db.session.execute(
                            db.text(
                                """
                                DELETE FROM devoir_vu 
                                WHERE devoir_id IN (
                                    SELECT id FROM devoir WHERE enseignant_id = :enseignant_id
                                )
                            """
                            ),
                            {"enseignant_id": enseignant.id},
                        )
                        db.session.execute(
                            db.text(
                                "DELETE FROM devoir WHERE enseignant_id = :enseignant_id"
                            ),
                            {"enseignant_id": enseignant.id},
                        )
                    except Exception as e:
                        current_app.logger.error(
                            f"Erreur lors de la suppression des devoirs: {str(e)}"
                        )
                        devoirs = Devoir.query.filter_by(
                            enseignant_id=enseignant.id
                        ).all()
                        for devoir in devoirs:
                            DevoirVu.query.filter_by(devoir_id=devoir.id).delete()
                            db.session.delete(devoir)

                    # Récupérer et supprimer les matières avec leurs dépendances
                    matieres_enseignant = Matiere.query.filter_by(
                        enseignant_id=enseignant.id
                    ).all()
                    for matiere in matieres_enseignant:
                        Presence.query.filter_by(matiere_id=matiere.id).delete()
                        Note.query.filter_by(matiere_id=matiere.id).delete()
                        EmploiTemps.query.filter_by(matiere_id=matiere.id).delete()
                        Devoir.query.filter_by(matiere_id=matiere.id).delete()
                        db.session.delete(matiere)

                    db.session.delete(enseignant)

                # Notifications de l'utilisateur
                Notification.query.filter_by(user_id=user_id).delete()

                # Enfin, supprimer l'utilisateur
                db.session.delete(user)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Utilisateur {user.nom} {user.prenom} supprimé avec succès.",
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erreur lors de la suppression de l'utilisateur {user_id}: {str(e)}"
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Erreur lors de la suppression : {str(e)}",
                }
            ),
            500,
        )


@admin_bp.route("/import/etudiants", methods=["POST"])
@login_required
def import_etudiants():
    """
    Fonction pour importer des étudiants.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))
    file = request.files.get("file")
    if not file:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for("admin.users"))
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        count = 0
        for _, row in df.iterrows():
            if User.query.filter_by(email=row["email"]).first():
                continue  # Ignore doublons
            user = User(
                nom=row["nom"],
                prenom=row["prenom"],
                email=row["email"],
                password_hash=generate_password_hash("defitech2024"),
                role="etudiant",
                date_naissance=row["date_naissance"],
                sexe=row["sexe"],
                age=18,  # Peut être recalculé
                statut="approuve",
                date_creation=datetime.now(),
            )
            db.session.add(user)
            db.session.commit()
            last_etudiant = Etudiant.query.order_by(Etudiant.id.desc()).first()
            if last_etudiant:
                try:
                    last_numero = int(last_etudiant.numero_etudiant.split("-")[-1])
                    new_numero = f"DEFI-{last_numero + 1:03d}"
                except Exception:
                    new_numero = "DEFI-001"
            else:
                new_numero = "DEFI-001"
            etudiant = Etudiant(
                user_id=user.id,
                filiere=row["filiere"],
                annee=row["annee"],
                numero_etudiant=new_numero,
            )
            db.session.add(etudiant)
            db.session.commit()
            count += 1
        flash(f"{count} étudiants importés avec succès.", "success")
    except Exception as e:
        flash(f"Erreur lors de l'import : {str(e)}", "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/template/etudiants")
@login_required
def download_etudiants_template():
    """
    Génère un fichier CSV modèle pour l'import des étudiants.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))

    output = io.StringIO()
    output.write("nom,prenom,email,date_naissance,sexe,filiere,annee\n")
    output.write(
        "Dupont,Alice,alice@exemple.com,2001-05-12,F,Informatique,1ère année\n"
    )
    output.write("Mensah,Koffi,koffi@exemple.com,2000-11-23,M,Génie Civil,2ème année\n")
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="etudiants_modele.csv",
    )


@admin_bp.route("/import/filieres", methods=["POST"])
@login_required
def import_filieres():
    """
    Fonction pour importer des filières.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))
    file = request.files.get("file")
    if not file:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for("admin.users"))
    try:
        import pandas as pd

        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        count = 0
        for _, row in df.iterrows():
            if Filiere.query.filter_by(nom=row["nom"]).first():
                continue  # Ignore doublons
            filiere = Filiere(nom=row["nom"], description=row["description"])
            db.session.add(filiere)
            db.session.commit()
            count += 1
        flash(f"{count} filières importées avec succès.", "success")
    except Exception as e:
        flash(f"Erreur lors de l'import : {str(e)}", "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/template/filieres")
@login_required
def download_filieres_template():
    """
    Route pour télécharger un modèle de fichier CSV pour les filières.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))

    output = io.StringIO()
    output.write("nom,description\n")
    output.write("Informatique,Développement et systèmes\n")
    output.write("Génie Civil,Construction et génie civil\n")
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="filieres_modele.csv",
    )


@admin_bp.route("/import/matieres", methods=["POST"])
@login_required
def import_matieres():
    """
    Route pour importer des matières depuis un fichier CSV ou Excel.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))
    file = request.files.get("file")
    if not file:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for("admin.users"))
    try:
        import pandas as pd

        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        count = 0
        for _, row in df.iterrows():
            filiere = Filiere.query.filter_by(nom=row["filiere"]).first()
            enseignant = User.query.filter_by(
                email=row["enseignant_email"], role="enseignant"
            ).first()
            if not filiere or not enseignant:
                continue
            ens_obj = Enseignant.query.filter_by(user_id=enseignant.id).first()
            if not ens_obj:
                continue
            if Matiere.query.filter_by(
                nom=row["nom"], filiere_id=filiere.id, enseignant_id=ens_obj.id
            ).first():
                continue
            matiere = Matiere(
                nom=row["nom"], filiere_id=filiere.id, enseignant_id=ens_obj.id
            )
            db.session.add(matiere)
            db.session.commit()
            count += 1
        flash(f"{count} matières importées avec succès.", "success")
    except Exception as e:
        flash(f"Erreur lors de l'import : {str(e)}", "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/template/matieres")
@login_required
def download_matieres_template():
    """
    Route pour télécharger un modèle de fichier CSV pour l'importation de matières.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))

    output = io.StringIO()
    output.write("nom,filiere,enseignant_email\n")
    output.write("Mathématiques,Informatique,prof.math@exemple.com\n")
    output.write("Programmation,Informatique,prof.info@exemple.com\n")
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="matieres_modele.csv",
    )


@admin_bp.route("/import/enseignants", methods=["POST"])
@login_required
def import_enseignants():
    """
    Route pour importer des enseignants depuis un fichier CSV ou Excel.
    """

    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))
    file = request.files.get("file")
    if not file:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for("admin.users"))
    try:
        import pandas as pd

        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        count = 0
        for _, row in df.iterrows():
            if User.query.filter_by(email=row["email"]).first():
                continue
            user = User(
                nom=row["nom"],
                prenom=row["prenom"],
                email=row["email"],
                password_hash=generate_password_hash("defitech2024"),
                role="enseignant",
                date_naissance=datetime(1980, 1, 1),
                sexe="M",
                age=40,
                statut="approuve",
                date_creation=datetime.now(),
            )
            db.session.add(user)
            db.session.commit()
            enseignant = Enseignant(
                user_id=user.id,
                specialite=row["specialite"],
                filieres_enseignees=row["filieres_enseignees"],
            )
            db.session.add(enseignant)
            db.session.commit()
            count += 1
        flash(f"{count} enseignants importés avec succès.", "success")
    except Exception as e:
        flash(f"Erreur lors de l'import : {str(e)}", "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/template/enseignants")
@login_required
def download_enseignants_template():
    """
    Route pour télécharger un modèle de fichier CSV pour l'importation d'enseignants.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))

    output = io.StringIO()
    output.write("nom,prenom,email,specialite,filieres_enseignees\n")
    output.write(
        "Martin,Jean,prof.math@exemple.com,Mathématiques,Informatique;Génie Civil\n"
    )
    output.write("Durand,Claire,prof.info@exemple.com,Programmation,Informatique\n")
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="enseignants_modele.csv",
    )


@admin_bp.route("/import/annees", methods=["POST"])
@login_required
def import_annees():
    """
    Route pour importer des années depuis un fichier CSV ou Excel.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))
    file = request.files.get("file")
    if not file:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for("admin.users"))
    try:
        import pandas as pd

        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        count = 0
        for _, row in df.iterrows():
            if Annee.query.filter_by(nom=row["nom"]).first():
                continue
            annee = Annee(nom=row["nom"])
            db.session.add(annee)
            db.session.commit()
            count += 1
        flash(f"{count} années importées avec succès.", "success")
    except Exception as e:
        flash(f"Erreur lors de l'import : {str(e)}", "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/template/annees")
@login_required
def download_annees_template():
    """
    Route pour télécharger un modèle de fichier CSV pour l'importation d'années.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("admin.users"))

    output = io.StringIO()
    output.write("nom\n")
    output.write("1ère année\n")
    output.write("2ème année\n")
    output.write("3ème année\n")
    output.write("Licence\n")
    output.write("Master\n")
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="annees_modele.csv",
    )


@admin_bp.route("/notes")
@login_required
def notes():
    """
    Route pour afficher la page des notes de l'administrateur.
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("main.index"))

    # Récupérer les filtres depuis la requête
    annee = request.args.get("annee")
    filiere = request.args.get("filiere")
    search = request.args.get("search", "").strip()

    notes_query = Note.query.join(Etudiant, Note.etudiant_id == Etudiant.id).join(
        User, Etudiant.user_id == User.id
    )

    if annee:
        notes_query = notes_query.filter(Etudiant.annee == annee)
    if filiere:
        notes_query = notes_query.filter(Etudiant.filiere == filiere)
    if search:
        notes_query = notes_query.filter(
            (User.nom.ilike(f"%{search}%")) | (User.prenom.ilike(f"%{search}%"))
        )

    notes_result = notes_query.all()
    annees = db.session.query(Etudiant.annee).distinct().all()
    filieres = db.session.query(Etudiant.filiere).distinct().all()

    return render_template(
        "admin/notes.html",
        notes=notes_result,
        annees=annees,
        filieres=filieres,
        selected_annee=annee,
        selected_filiere=filiere,
        search=search,
    )
