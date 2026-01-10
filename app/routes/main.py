from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    jsonify,
    request,
)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.suggestion import Suggestion, SuggestionVote
from app.models.notification import Notification
from app.models.user import User
from app.email_utils import send_email
import secrets
import logging
import datetime

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.route("/")
def index():
    """
    Page d'accueil (Landing Page).
    Si l'utilisateur est déjà connecté, on pourrait lui proposer un bouton vers son dashboard dans le template.
    """
    current_year = datetime.datetime.now().year
    return render_template("index.html", current_year=current_year)


@main_bp.route("/confidentialite")
def confidentialite():
    """Page de politique de confidentialité."""
    if request.is_json or request.args.get("format") == "json":
        # Data extracted from the template's JavaScript
        sections = [
            {
                "title": "Quelles données personnelles collectons-nous ?",
                "subtitle": "Liste complète et détaillée par catégorie",
                "content": "Identification (Nom, Email, N° étudiant), Données académiques (Filière, Notes, Présences), Données techniques (IP, Cookies).",
            },
            {
                "title": "Pourquoi collectons-nous ces données ?",
                "subtitle": "8 finalités légitimes et précises",
                "content": "Gérer votre compte, Accès aux cours/notes, Sécurité, Analyse d'usage, Alertes pédagogiques, Support technique, Statistiques, Obligations légales.",
            },
            {
                "title": "Sur quelle base légale ?",
                "subtitle": "RGPD + loi togolaise",
                "content": "Exécution du service, Intérêt légitime, Obligation légale, Consentement.",
            },
            {
                "title": "Combien de temps gardons-nous vos données ?",
                "subtitle": "Durées de conservation",
                "content": "Compte: 3 ans d'inactivité. Notes: 50 ans. Logs: 12 mois. Cookies: 13 mois.",
            },
            {
                "title": "À qui transmettons-nous vos données ?",
                "subtitle": "Destinataires autorisés",
                "content": "Personnel administratif, Enseignants, Équipe IT, Hébergeur (OVHcloud). AUCUNE VENTE DE DONNÉES.",
            },
            {
                "title": "Vos droits",
                "subtitle": "Accès, suppression, etc.",
                "content": "Accès, Rectification, Suppression, Limitation, Opposition, Portabilité, Retrait de consentement.",
            },
            {
                "title": "Sécurité",
                "subtitle": "Protection des données",
                "content": "Chiffrement HTTPS, Mots de passe hachés, 2FA disponible, Sauvegardes chiffrées.",
            },
        ]
        return jsonify(
            {
                "success": True,
                "title": "Politique de Confidentialité",
                "last_update": "21 novembre 2025",
                "sections": sections,
            }
        )
    return render_template("confidentialite.html")


@main_bp.route("/mentions-legales")
def mentions_legales():
    """Page des mentions légales."""
    if request.is_json or request.args.get("format") == "json":
        return jsonify(
            {
                "success": True,
                "title": "Mentions Légales",
                "data": {
                    "editeur": "Université DEFITECH",
                    "adresse": "123 Avenue de l'Université, Ville, Pays",
                    "email": "contact@defitech.com",
                    "telephone": "+22 22 22 22",
                    "directeur_publication": "Mr. Ambroise AMETOESSO",
                    "hebergeur": "OVH, 2 rue Kellermann, 59100 Roubaix, France",
                    "propriete": "Tous les contenus présents sur ce site sont la propriété exclusive de l'Université DEFITECH.",
                },
            }
        )
    return render_template("mentions_legales.html")


@main_bp.route("/roadmap")
def roadmap():
    """Page de la roadmap du projet."""
    if request.is_json or request.args.get("format") == "json":
        # Structured roadmap data extracted from the template
        roadmap_data = [
            {
                "category": "Paiement & Finances",
                "icon": "credit-card",
                "color": "green",
                "items": [
                    {
                        "title": "Paiement de Scolarité en Ligne",
                        "description": "Système de paiement sécurisé via Mobile Money et cartes bancaires.",
                        "status": "Planifié 2026",
                        "status_code": "planned",
                        "features": [
                            "Paiement fractionné",
                            "Reçus automatiques",
                            "Suivi historique",
                        ],
                    },
                    # ... other items would be added here in a real scenario
                    # for now adding a few illustrative ones
                    {
                        "title": "Gestion des Bourses",
                        "description": "Suivi des bourses d'études et aides financières.",
                        "status": "En conception",
                        "status_code": "design",
                        "features": ["Dépôt de dossier", "Suivi d'attribution"],
                    },
                ],
            },
            {
                "category": "Outils & Productivité",
                "icon": "tools",
                "color": "orange",
                "items": [
                    {
                        "title": "Application Mobile DEFITECH",
                        "description": "Accédez à DEFITECH partout avec notre application mobile iOS et Android.",
                        "status": "En développement",
                        "status_code": "dev",
                        "features": [
                            "Mode hors ligne",
                            "Notifications push",
                            "Sync instantanée",
                        ],
                    },
                    {
                        "title": "Tableau de Bord Personnel",
                        "description": "Suivez vos performances académiques avec des statistiques détaillées.",
                        "status": "Disponible",
                        "status_code": "available",
                        "features": [
                            "Évolution des notes",
                            "Taux de présence",
                            "Progression",
                        ],
                    },
                ],
            },
        ]
        return jsonify(
            {
                "success": True,
                "title": "Feuille de Route 2025-2026",
                "sections": roadmap_data,
            }
        )
    return render_template("roadmap.html")


@main_bp.route("/image-search")
@login_required
def image_search():
    """Point d'entrée pour la recherche d'images par IA."""
    return render_template("image_search/index.html")


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
    try:
        return redirect(url_for("ai_assistant.chat"))
    except Exception as e:
        logger.error("Erreur lors de la redirection vers l'API du chat : {}".format(e))


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
    return render_template("errors/404.html"), 404


@main_bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html"), 500


@main_bp.route("/suggestions")
def suggestions():
    """
    Page publique de la boîte à suggestions
    """
    suggestions_list = (
        Suggestion.query.filter_by(statut="ouverte")
        .order_by(Suggestion.date_creation.desc())
        .all()
    )

    suggestions_data = []
    for suggestion in suggestions_list:
        suggestions_data.append(
            {"suggestion": suggestion, "reponses": suggestion.reponses}
        )

    if request.is_json or request.args.get("format") == "json":
        session_id = request.cookies.get("suggestion_session_id")
        user_id = current_user.id if current_user.is_authenticated else None

        data = []
        for item in suggestions_data:
            s = item["suggestion"]
            data.append(
                {
                    "id": s.id,
                    "content": s.contenu,
                    "author": s.auteur_anonyme or "Incognito",
                    "date": s.date_creation.strftime("%d/%m/%Y à %H:%M"),
                    "status": s.statut,
                    "votes_oui": s.votes_oui,
                    "votes_non": s.votes_non,
                    "total_votes": s.total_votes,
                    "user_vote": (
                        s.get_user_vote(
                            user_id=user_id, session_id=session_id
                        ).type_vote
                        if s.has_user_voted(user_id=user_id, session_id=session_id)
                        else None
                    ),
                    "responses": [
                        {
                            "content": r.contenu,
                            "date": r.date_creation.strftime("%d/%m/%Y à %H:%M"),
                        }
                        for r in item["reponses"]
                    ],
                }
            )

        return jsonify(
            {
                "success": True,
                "count": len(data),
                "data": data,
                "stats": {
                    "total_suggestions": len(data),
                    "total_oui": sum(s.votes_oui for s in suggestions_list),
                    "total_non": sum(s.votes_non for s in suggestions_list),
                    "total_participation": sum(s.total_votes for s in suggestions_list),
                },
            }
        )

    return render_template("suggestions.html", suggestions_data=suggestions_data)


@main_bp.route("/suggestions", methods=["POST"])
def submit_suggestion():
    """
    Soumission d'une nouvelle suggestion
    """
    contenu = request.form.get("contenu", "").strip()
    auteur_anonyme = request.form.get("auteur_anonyme", "").strip()
    email_contact = request.form.get("email_contact", "").strip()

    if not contenu:
        flash("Le contenu de la suggestion ne peut pas être vide.", "error")
        return redirect(url_for("main.suggestions"))

    if len(contenu) < 10:
        flash("La suggestion doit contenir au moins 10 caractères.", "error")
        return redirect(url_for("main.suggestions"))

    if len(contenu) > 1000:
        flash("La suggestion ne peut pas dépasser 1000 caractères.", "error")
        return redirect(url_for("main.suggestions"))

    suggestion = Suggestion(
        contenu=contenu,
        auteur_anonyme=auteur_anonyme if auteur_anonyme else None,
        email_contact=email_contact if email_contact else None,
        statut="ouverte",
    )

    db.session.add(suggestion)
    db.session.commit()

    try:
        admins = User.query.filter_by(role="admin").all()
        for admin in admins:
            notif = Notification(
                user_id=admin.id,
                message=f"Nouvelle suggestion soumise : {contenu[:50]}{'...' if len(contenu) > 50 else ''}",
                type="info",
            )
            db.session.add(notif)

            try:
                send_email(
                    to=admin.email,
                    subject="Nouvelle suggestion - DEFITECH",
                    template_name="suggestion_notification",
                    admin=admin,
                    suggestion=suggestion,
                )
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email : {e}")

        db.session.commit()
    except Exception as e:
        print(f"Erreur lors de la notification : {e}")

    flash("Votre suggestion a été soumise avec succès !", "success")
    return redirect(url_for("main.suggestions"))


@main_bp.route("/suggestions/vote", methods=["POST"])
def vote_suggestion():
    """
    Vote sur une suggestion (Oui/Non)
    """
    suggestion_id = request.form.get("suggestion_id", type=int)
    vote_type = request.form.get("vote_type")  # 'oui' ou 'non'

    if not suggestion_id or vote_type not in ["oui", "non"]:
        flash("Données de vote invalides.", "error")
        return redirect(url_for("main.suggestions"))

    suggestion = Suggestion.query.get_or_404(suggestion_id)

    user_id = current_user.id if current_user.is_authenticated else None
    session_id = request.cookies.get("suggestion_session_id")

    response = redirect(url_for("main.suggestions"))

    if not session_id:
        session_id = secrets.token_urlsafe(32)
        response.set_cookie(
            "suggestion_session_id", session_id, max_age=365 * 24 * 60 * 60
        )

    if suggestion.has_user_voted(user_id=user_id, session_id=session_id):
        flash("Vous avez déjà voté sur cette suggestion.", "warning")
        return response

    vote = SuggestionVote(
        suggestion_id=suggestion_id,
        user_id=user_id,
        session_id=session_id if not user_id else None,
        type_vote=vote_type,
    )

    db.session.add(vote)
    db.session.commit()

    action_text = "approuvé" if vote_type == "oui" else "rejeté"
    if request.is_json:
        return jsonify(
            {
                "success": True,
                "message": f"Vous avez {action_text} cette suggestion.",
                "votes_oui": suggestion.votes_oui,
                "votes_non": suggestion.votes_non,
                "total_votes": suggestion.total_votes,
            }
        )
    return response


@main_bp.route("/verify/doc/<int:doc_id>")
def verify_doc(doc_id):
    """
    Route publique pour vérifier l'authenticité d'un relevé de notes.
    Accessible via QR Code.
    """
    from app.models.academic import AcademicArchivedStudent

    doc = AcademicArchivedStudent.query.get(doc_id)
    if not doc:
        return render_template("errors/404.html"), 404

    return render_template("documents/verify_result.html", doc=doc)
