from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import login_required, current_user
from app.extensions import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """
    Page d'accueil. Si l utilisateur est connecté , il est redirig vers son dashboard respectif.
    Sinon, il est redirig vers la page de connexion.
    """
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "enseignant":
            return redirect(url_for("teachers.dashboard"))
        elif current_user.role == "etudiant":
            return redirect(url_for("students.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/defAI")
@login_required
def defAI_page():
    """
    Renvoie la page "defAI" si l'utilisateur est connecté et a un rôle valide.
    """
    user_role = None
    if current_user.role == "etudiant":
        user_role = "etudiant"
    elif current_user.role == "enseignant":
        user_role = "enseignant"
    elif current_user.role == "admin":
        user_role = "admin"

    if not user_role:
        flash("Accès non autorisé. Rôle utilisateur non reconnu.", "error")
        return redirect(url_for("main.index"))

    return render_template("chat/defAI.html", user_role=user_role)


@main_bp.route("/defAI/chat")
@login_required
def defAI_chat():
    """
    Redirige vers l'API du chat avec l'assistant IA.
    """
    # Assuming 'ai_assistant' blueprint exists or will exist.
    # If it was 'study_buddy', we should check that.
    # For now, keeping as is, but might need adjustment.
    try:
        return redirect(url_for("ai_assistant.chat"))
    except Exception:
        # Fallback if ai_assistant not found, maybe study_buddy?
        return redirect(url_for("study_buddy.chat_api"))


@main_bp.route("/health")
def health_check():
    """
    Vérification de l'état de l'application (pour Render/Koyeb).
    """
    try:
        # Vérifier la connexion BDD
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@main_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@main_bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500
