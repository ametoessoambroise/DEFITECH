from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import check_password_hash
from app.models.user import User
from app.services.jwt_service import JWTService
from app.utils.cloudinary_utils import upload_to_cloudinary
import functools

api_bp = Blueprint("api", __name__, url_prefix="/api")


def token_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            print(f"❌ Token manquant. Headers: {dict(request.headers)}")
            return jsonify({"message": "Token manquant"}), 401

        user_id = JWTService.decode_token(token)
        print(f"🔍 Token décodé: user_id={user_id}, type={type(user_id)}")

        if isinstance(user_id, str):
            print(f"❌ Erreur JWT: {user_id}")
            return jsonify({"message": user_id}), 401

        current_user = User.query.get(user_id)
        if not current_user:
            print(f"❌ Utilisateur non trouvé pour ID: {user_id}")
            return jsonify({"message": "Utilisateur non trouvé"}), 401

        print(f"✅ Authentification réussie: {current_user.email}")
        return f(current_user, *args, **kwargs)

    return decorated


@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"message": "Identifiants manquants"}), 400

    user = User.query.filter_by(email=data.get("email")).first()

    if user and check_password_hash(user.password_hash, data.get("password")):
        if user.statut != "approuve":
            return jsonify({"message": "Compte non approuvé"}), 401

        token = JWTService.generate_token(user.id)
        return jsonify(
            {
                "success": True,
                "token": token,
                "user": {
                    "id": user.id,
                    "nom": user.nom,
                    "prenom": user.prenom,
                    "email": user.email,
                    "role": user.role,
                },
            }
        )

    return jsonify({"message": "Email ou mot de passe incorrect"}), 401


@api_bp.route("/auth/verify-token", methods=["POST"])
@token_required
def verify_token(current_user):
    return jsonify(
        {
            "success": True,
            "user": {
                "id": current_user.id,
                "nom": current_user.nom,
                "prenom": current_user.prenom,
                "email": current_user.email,
                "role": current_user.role,
            },
        }
    )


@api_bp.route("/projects", methods=["GET"])
@token_required
def get_projects(current_user):
    from app.models.projet import Projet

    projets = Projet.query.filter_by(user_id=current_user.id).all()
    return jsonify([p.to_dict() for p in projets])


@api_bp.route("/projects/sync", methods=["POST"])
@token_required
def sync_project(current_user):
    from app.models.projet import Projet
    from app.extensions import db
    import json
    from werkzeug.utils import secure_filename

    # Récupération des métadonnées
    titre = request.form.get("titre")
    description = request.form.get("description", "")
    technologies = request.form.get("technologies", "")
    structure_json_data = request.form.get("structure_json")

    if not titre:
        return jsonify({"message": "Le titre du projet est requis"}), 400

    if "project_zip" not in request.files:
        return jsonify({"message": "Fichier ZIP manquant"}), 400

    zip_file = request.files["project_zip"]

    # Chercher si le projet existe déjà pour cet utilisateur
    project = Projet.query.filter_by(user_id=current_user.id, titre=titre).first()

    if not project:
        # Création d'un nouveau projet
        project = Projet(
            user_id=current_user.id,
            titre=titre,
            description=description,
            technologies=technologies,
            en_cours=True,
        )
        db.session.add(project)
        db.session.flush()  # Pour avoir l'ID
    else:
        # Mise à jour des métadonnées si fournies
        if description:
            project.description = description
        if technologies:
            project.technologies = technologies

    # Sauvegarde du ZIP sur Cloudinary
    try:
        filename = secure_filename(f"project_{project.id}_{current_user.id}.zip")
        upload_result = upload_to_cloudinary(
            zip_file.stream, filename, folder="projects", resource_type="raw"
        )
        project.lien = upload_result.get("secure_url")
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'upload Cloudinary: {str(e)}")
        # Optionnel: on peut garder un fallback local ou retourner une erreur
        return (
            jsonify(
                {"message": "Erreur lors de la sauvegarde du fichier sur le cloud"}
            ),
            500,
        )
    if structure_json_data:
        try:
            project.structure_json = json.loads(structure_json_data)
        except json.JSONDecodeError:
            pass  # On ignore si le JSON est corrompu

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "Projet synchronisé avec succès",
            "project": project.to_dict(),
        }
    )


# ========================================
# DEFAI CODE ASSISTANT ENDPOINTS
# ========================================


@api_bp.route("/defai/chat", methods=["POST"])
@token_required
def defai_chat(current_user):
    """
    Endpoint pour les requêtes de chat DEFAI depuis VS Code.

    Reçoit un message avec contexte de code et retourne une réponse enrichie.

    Request Body:
        {
            "message": "Explique cette fonction",
            "language": "python",
            "code": "def process_data(...)...",
            "file_path": "src/utils.py",
            "project_id": 123  // Optional
        }

    Returns:
        {
            "success": true,
            "reply": "Réponse de DEFAI...",
            "conversation_id": 456,
            "message_id": 789
        }
    """
    from app.services.defai_code_assistant import DefaiCodeAssistantService
    from app.models.ai_assistant import AIConversation, AIMessage
    from app.routes.ai_assistant import call_gemini_api, orchestrator
    from app.extensions import db
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)

    try:
        data = request.get_json()

        if not data or not data.get("message"):
            return jsonify({"success": False, "error": "Message manquant"}), 400

        message = data.get("message", "").strip()
        language = data.get("language")
        code = data.get("code")
        file_path = data.get("file_path", "unknown.txt")
        project_id = data.get("project_id")
        conversation_id = data.get("conversation_id")

        # Extraire le contexte de code
        code_context = DefaiCodeAssistantService.extract_context(
            file_path=file_path, selected_code=code, language=language
        )

        # Déterminer le rôle de l'utilisateur et mapper vers l'anglais
        role_mapping = {
            "etudiant": "student",
            "enseignant": "teacher",
            "admin": "admin",
        }
        user_role_fr = (
            current_user.role if hasattr(current_user, "role") else "etudiant"
        )
        user_role = role_mapping.get(user_role_fr, "student")

        # Créer ou récupérer la conversation
        if not conversation_id:
            # Créer une nouvelle conversation liée au projet si fourni
            conversation = AIConversation(
                user_id=current_user.id,
                user_role=user_role,
                title=(
                    f"Code: {file_path.split('/')[-1]}"
                    if file_path
                    else "Conversation VS Code"
                ),
                created_at=datetime.utcnow(),
            )
            db.session.add(conversation)
            db.session.flush()
            conversation_id = conversation.id
        else:
            conversation = AIConversation.query.get(conversation_id)
            if not conversation or conversation.user_id != current_user.id:
                return (
                    jsonify({"success": False, "error": "Conversation non trouvée"}),
                    404,
                )

        # Préparer le payload enrichi
        payload = DefaiCodeAssistantService.prepare_defai_payload(
            message=message,
            code_context=code_context,
            project_id=project_id,
            user_id=current_user.id,
        )

        # Sauvegarder le message utilisateur avec contexte de code
        user_message = AIMessage(
            conversation_id=conversation_id,
            message_type="user",
            content=message,
            extra_data={
                "code_context": {
                    "language": code_context.language,
                    "file_path": code_context.file_path,
                    "has_selection": code_context.selected_code is not None,
                },
                "source": "vscode_extension",
            },
            created_at=datetime.utcnow(),
            message_order=AIMessage.query.filter_by(
                conversation_id=conversation_id
            ).count()
            + 1,
        )
        db.session.add(user_message)
        db.session.flush()

        # Récupérer le contexte utilisateur
        context_data = orchestrator.get_user_context(current_user.id, user_role)

        # Enrichir le contexte avec les informations de code
        enhanced_context = DefaiCodeAssistantService.enrich_context_for_gemini(
            context_data, code_context
        )

        # Récupérer l'historique de conversation (derniers 10 messages)
        previous_messages = (
            AIMessage.query.filter_by(conversation_id=conversation_id)
            .order_by(AIMessage.created_at.desc())
            .limit(10)
            .all()
        )

        # Formater l'historique pour Gemini
        messages_history = [
            {
                "message_type": msg.message_type,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in reversed(previous_messages)
        ]

        # Construire le message enrichi pour Gemini
        gemini_message = message
        if code_context.selected_code:
            code_formatted = DefaiCodeAssistantService.format_code_for_ai(
                code_context.selected_code, code_context.language
            )
            gemini_message = f"{message}\n\n**Code concerné:**\n{code_formatted}"

        # Appeler Gemini
        gemini_response = call_gemini_api(
            gemini_message, enhanced_context, messages_history, attachments=[]
        )

        if not gemini_response["success"]:
            error_message = f"Erreur: {gemini_response['error']}"

            # Sauvegarder l'erreur
            error_msg = AIMessage(
                conversation_id=conversation_id,
                message_type="assistant",
                content=error_message,
                extra_data={"error": True, "source": "vscode_extension"},
                message_order=AIMessage.query.filter_by(
                    conversation_id=conversation_id
                ).count()
                + 1,
                created_at=datetime.utcnow(),
            )
            db.session.add(error_msg)
            db.session.commit()

            return jsonify({"success": False, "error": gemini_response["error"]}), 500

        ai_response = gemini_response["response"]

        # Sauvegarder la réponse de l'assistant
        assistant_message = AIMessage(
            conversation_id=conversation_id,
            message_type="assistant",
            content=ai_response,
            extra_data={
                "finish_reason": gemini_response.get("finish_reason", "STOP"),
                "grounding_metadata": gemini_response.get("grounding_metadata", {}),
                "has_web_search": gemini_response.get("has_web_search", False),
                "source": "vscode_extension",
            },
            created_at=datetime.utcnow(),
            message_order=AIMessage.query.filter_by(
                conversation_id=conversation_id
            ).count()
            + 1,
        )
        db.session.add(assistant_message)
        db.session.commit()

        logger.info(
            f"DEFAI chat réussi pour utilisateur {current_user.id}, conversation {conversation_id}"
        )

        return jsonify(
            {
                "success": True,
                "reply": ai_response,
                "conversation_id": conversation_id,
                "message_id": assistant_message.id,
                "grounding_metadata": gemini_response.get("grounding_metadata", {}),
                "has_web_search": gemini_response.get("has_web_search", False),
            }
        )

    except Exception as e:
        logger.exception(f"Erreur DEFAI chat: {e}")
        return (
            jsonify(
                {"success": False, "error": "Erreur serveur interne", "details": str(e)}
            ),
            500,
        )


@api_bp.route("/defai/conversations", methods=["GET"])
@token_required
def get_defai_conversations(current_user):
    """
    Récupère les conversations DEFAI de l'utilisateur.

    Query Parameters:
        - project_id (optional): Filtrer par projet
        - limit (optional): Nombre max de conversations (défaut: 20)

    Returns:
        {
            "success": true,
            "conversations": [...]
        }
    """
    from app.models.ai_assistant import AIConversation, AIMessage
    from sqlalchemy import desc
    import logging

    logger = logging.getLogger(__name__)

    try:
        project_id = request.args.get("project_id", type=int)
        limit = request.args.get("limit", 20, type=int)

        # Requête de base: conversations de l'utilisateur provenant de VS Code
        query = AIConversation.query.filter_by(user_id=current_user.id)

        # Filtrer par source (messages provenant de l'extension)
        # On cherche les conversations qui ont au moins un message de source vscode_extension
        query = (
            query.join(AIMessage)
            .filter(AIMessage.metadata.op("->>")("source") == "vscode_extension")
            .distinct()
        )

        # Limiter le nombre de résultats
        conversations = (
            query.order_by(desc(AIConversation.created_at)).limit(limit).all()
        )

        # Formater les conversations
        formatted_conversations = []
        for conv in conversations:
            # Récupérer le dernier message
            last_message = (
                AIMessage.query.filter_by(conversation_id=conv.id)
                .order_by(desc(AIMessage.created_at))
                .first()
            )

            formatted_conversations.append(
                {
                    "id": conv.id,
                    "title": conv.title,
                    "created_at": (
                        conv.created_at.isoformat() if conv.created_at else None
                    ),
                    "last_message": (
                        last_message.content[:100] + "..."
                        if last_message and len(last_message.content) > 100
                        else (last_message.content if last_message else None)
                    ),
                    "message_count": AIMessage.query.filter_by(
                        conversation_id=conv.id
                    ).count(),
                }
            )

        logger.info(
            f"Récupération de {len(formatted_conversations)} conversations DEFAI pour utilisateur {current_user.id}"
        )

        return jsonify({"success": True, "conversations": formatted_conversations})

    except Exception as e:
        logger.exception(f"Erreur récupération conversations DEFAI: {e}")
        return (
            jsonify(
                {"success": False, "error": "Erreur serveur interne", "details": str(e)}
            ),
            500,
        )
