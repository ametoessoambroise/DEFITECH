"""
Blueprint pour la messagerie en temps réel (Chat)
Permet aux utilisateurs d'envoyer des messages à l'admin et à l'admin de répondre
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from app.extensions import db, socketio
from app.models.message import Message
from app.models.user import User
from datetime import datetime
from sqlalchemy import or_, func

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


@chat_bp.before_request
@login_required
def check_app_lock():
    from app.utils.decorators import app_lock_required

    @app_lock_required
    def protected():
        pass

    return protected()


# ==================== ROUTES HTML ====================


@chat_bp.route("/")
@login_required
def index():
    """
    Cette fonction redirige vers l'interface appropriée
    selon le rôle de l'utilisateur.

    Si le rôle est "admin", l'utilisateur est redirigé vers
    l'interface multi-conversations.

    Si le rôle est autre que "admin", l'utilisateur est redirigé vers
    l'interface de chat avec l'administrateur.
    """
    if current_user.role == "admin":
        return redirect(url_for("chat.admin_chat"))
    else:
        return redirect(url_for("chat.user_chat"))


@chat_bp.route("/user")
@login_required
def user_chat():
    """
    Interface de chat pour les utilisateurs (étudiants, enseignants).

    Cette fonction permet aux utilisateurs authentifiés (étudiants et
    enseignants) de communiquer avec l'administrateur en envoyant des
    messages.

    Args:
        None

    Returns:
        Une réponse redirigeant vers l'interface de chat avec l'administrateur
        si le rôle de l'utilisateur est différent de "admin", sinon une
        réponse redirigeant vers l'interface multi-conversations.

    """
    if current_user.role == "admin":
        flash("Les administrateurs doivent utiliser l'interface admin.", "info")
        return redirect(url_for("chat.admin_chat"))

    # Récupérer l'admin (supposons que le premier admin est l'admin principal)
    admin = User.query.filter_by(role="admin").first()
    if not admin:
        flash("Aucun administrateur disponible pour le chat.", "error")
        return redirect(url_for("main.index"))

    # Récupérer tous les admins pour la liste
    admins = User.query.filter_by(role="admin").all()

    return render_template("chat/user_chat.html", admin=admin, admins=admins)


@chat_bp.route("/admin")
@login_required
def admin_chat():
    """
    Interface de chat pour les administrateurs

    Cette fonction permet aux administrateurs de communiquer avec différents
    utilisateurs en vue de résoudre des problèmes ou de fournir des
    informations. Elle affiche la liste des conversations en cours et permet
    de répondre à chaque conversation.

    Args:
        None

    Returns:
        Une réponse redirigeant vers l'interface de chat avec les utilisateurs
        si le rôle de l'utilisateur est "admin", sinon une réponse redirigeant
        vers l'interface de chat avec l'administrateur.
    """
    if current_user.role != "admin":
        flash("Accès réservé aux administrateurs.", "error")
        return redirect(url_for("chat.user_chat"))

    return render_template("chat/admin_chat.html")


# ==================== API ENDPOINTS ====================


@chat_bp.route("/api/history")
@login_required
def get_history():
    """
    Récupère l'historique des messages entre l'utilisateur connecté et un autre utilisateur.

    Cette API permet de récupérer l'historique des messages échangés entre l'utilisateur connecté
    et un autre utilisateur spécifié par le paramètre 'with'.

    Args:
        None

    Paramètres de requête:
        - with (int): Identifiant de l'utilisateur avec qui on veut voir l'historique.
        - limit (int, optionnel): Nombre de messages à renvoyer (valeur par défaut: 50).
        - offset (int, optionnel): Décalage de pagination (valeur par défaut: 0).

    Retourne:
        Une réponse JSON contenant la liste des messages de l'historique.

    Exemple de requête:
        GET /api/history?with=123&limit=50&offset=0

    Exemple de réponse:
        {
            "success": true,
            "messages": [
                {
                    "id": 1,
                    "sender_id": 123,
                    "receiver_id": 456,
                    "content": "Bonjour",
                    "timestamp": "2022-01-01T00:00:00",
                    "is_read": false
                },
                {
                    "id": 2,
                    "sender_id": 456,
                    "receiver_id": 123,
                    "content": "Bonjour à vous aussi",
                    "timestamp": "2022-01-01T00:01:00",
                    "is_read": true
                }
            ]
        }
    """
    other_user_id = request.args.get("with", type=int)
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    if not other_user_id:
        return jsonify({"success": False, "error": "Paramètre 'with' requis"}), 400

    # Vérifier que l'autre utilisateur existe
    other_user = User.query.get(other_user_id)
    if not other_user:
        return jsonify({"success": False, "error": "Utilisateur non trouvé"}), 404

    # Récupérer l'historique
    messages = Message.get_conversation(
        current_user.id, other_user_id, limit=limit, offset=offset
    )

    # Marquer les messages reçus comme lus
    unread_messages = [
        msg
        for msg in messages
        if msg.receiver_id == current_user.id and not msg.is_read
    ]
    for msg in unread_messages:
        msg.mark_as_read(commit=False)
    if unread_messages:
        db.session.commit()

    return jsonify(
        {
            "success": True,
            "messages": [msg.to_dict() for msg in messages],
            "other_user": {
                "id": other_user.id,
                "nom": other_user.nom,
                "prenom": other_user.prenom,
                "email": other_user.email,
                "photo_profil": other_user.photo_profil,
            },
        }
    )


@chat_bp.route("/api/conversations")
@login_required
def get_conversations():
    """
    Permet à l'administrateur de récupérer la liste des conversations
    qui ont eu lieu avec lui. Cette fonction renvoie la liste des utilisateurs
    qui ont échangé avec l'administrateur, ainsi que le dernier message envoyé
    dans chaque conversation.

    Args:
        None

    Returns:
        Une réponse JSON contenant les informations suivantes :
        - success (bool): Indique si la requête a été effectuée avec succès
        - conversations (list): Liste des conversations avec les utilisateurs
            - id (int): Identifiant de l'utilisateur
            - nom (str): Nom de l'utilisateur
            - prenom (str): Prénom de l'utilisateur
            - email (str): Adresse e-mail de l'utilisateur
            - photo_profil (str): Chemin vers la photo de profil de l'utilisateur
            - dernier_message (dict): Informations sur le dernier message envoyé
                - id (int): Identifiant du message
                - sender_id (int): Identifiant de l'expéditeur
                - receiver_id (int): Identifiant du destinataire
                - contenu (str): Contenu du message
                - timestamp (str): Date et heure de l'envoi du message au format ISO 8601
                - is_read (bool): Indique si le message a été lu

    Exemple de réponse JSON :
    {
        "success": true,
        "conversations": [
            {
                "id": 1,
                "nom": "Doe",
                "prenom": "John",
                "email": "john.doe@example.com",
                "photo_profil": "/static/photos/profil/john_doe.png",
                "dernier_message": {
                    "id": 1,
                    "sender_id": 1,
                    "receiver_id": 2,
                    "contenu": "Bonjour",
                    "timestamp": "2022-01-01T00:00:00",
                    "is_read": false
                }
            },
            {
                "id": 2,
                "nom": "Smith",
                "prenom": "Jane",
                "email": "jane.smith@example.com",
                "photo_profil": "/static/photos/profil/jane_smith.png",
                "dernier_message": {
                    "id": 2,
                    "sender_id": 2,
                    "receiver_id": 1,
                    "contenu": "Bonjour John",
                    "timestamp": "2022-01-01T00:01:00",
                    "is_read": true
                }
            }
        ]
    }
    """
    if current_user.role != "admin":
        return (
            render_template(
                "error.html", title="Accès non autorisé", message="Accès non autorisé"
            ),
            403,
        )

    # Requête pour obtenir les utilisateurs avec qui l'admin a échangé
    # et le dernier message de chaque conversation
    subquery = (
        db.session.query(
            func.max(Message.id).label("max_id"),
            Message.sender_id,
            Message.receiver_id,
        )
        .filter(
            or_(
                Message.sender_id == current_user.id,
                Message.receiver_id == current_user.id,
            )
        )
        .group_by(Message.sender_id, Message.receiver_id)
        .subquery()
    )

    # Récupérer les derniers messages
    last_messages = (
        db.session.query(Message)
        .join(subquery, Message.id == subquery.c.max_id)
        .order_by(Message.timestamp.desc())
        .all()
    )

    # Construire la liste des conversations
    conversations = {}
    for msg in last_messages:
        # Déterminer l'autre utilisateur (pas l'admin)
        other_user_id = (
            msg.sender_id if msg.sender_id != current_user.id else msg.receiver_id
        )

        if other_user_id not in conversations:
            other_user = User.query.get(other_user_id)
            if other_user:
                # Compter les messages non lus de cet utilisateur
                unread_count = Message.query.filter_by(
                    sender_id=other_user_id,
                    receiver_id=current_user.id,
                    is_read=False,
                ).count()

                conversations[other_user_id] = {
                    "user": {
                        "id": other_user.id,
                        "nom": other_user.nom,
                        "prenom": other_user.prenom,
                        "email": other_user.email,
                        "role": other_user.role,
                        "photo_profil": other_user.photo_profil,
                    },
                    "last_message": {
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "is_from_me": msg.sender_id == current_user.id,
                    },
                    "unread_count": unread_count,
                }

    return jsonify({"success": True, "conversations": list(conversations.values())})


@chat_bp.route("/api/unread-count")
@login_required
def get_unread_count():
    """
    Récupère le nombre total de messages non lus pour l'utilisateur connecté.

    Cette fonction utilise une requête SQL pour compter le nombre de messages
    non lus pour l'utilisateur connecté en utilisant la colonne 'is_read'.

    Returns:
        int: Le nombre total de messages non lus pour l'utilisateur connecté.
    """
    unread_count = Message.query.filter_by(
        receiver_id=current_user.id, is_read=False
    ).count()

    return jsonify({"success": True, "unread_count": unread_count})


# ==================== SOCKET.IO EVENT HANDLERS ====================


@socketio.on("connect")
def handle_connect():
    """Gère la connexion d'un utilisateur au chat"""
    if current_user.is_authenticated:
        # Rejoindre une room personnelle (identifiée par l'ID utilisateur)
        join_room(f"user_{current_user.id}")
        emit("connected", {"user_id": current_user.id, "message": "Connecté au chat"})
        print(f"[CHAT] User {current_user.id} ({current_user.nom}) connected to chat")


@socketio.on("disconnect")
def handle_disconnect():
    """Gère la déconnexion d'un utilisateur"""
    if current_user.is_authenticated:
        leave_room(f"user_{current_user.id}")
        print(
            f"[CHAT] User {current_user.id} ({current_user.nom}) disconnected from chat"
        )


@socketio.on("send_message")
def handle_send_message(data):
    """
    Gère l'envoi d'un message
    Data attendue:
        - receiver_id (int): ID du destinataire
        - content (str): Contenu du message
    """
    if not current_user.is_authenticated:
        emit("error", {"message": "Non authentifié"})
        return

    receiver_id = data.get("receiver_id")
    content = data.get("content", "").strip()

    # Validation
    if not receiver_id:
        emit("error", {"message": "Destinataire non spécifié"})
        return

    if not content:
        emit("error", {"message": "Le message ne peut pas être vide"})
        return

    if len(content) > 5000:
        emit("error", {"message": "Le message est trop long (max 5000 caractères)"})
        return

    # Vérifier que le destinataire existe
    receiver = User.query.get(receiver_id)
    if not receiver:
        emit("error", {"message": "Destinataire non trouvé"})
        return

    try:
        # Créer et sauvegarder le message
        message = Message(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            content=content,
            timestamp=datetime.utcnow(),
            is_read=False,
        )
        db.session.add(message)
        db.session.commit()

        # Préparer les données du message
        message_data = {
            "id": message.id,
            "sender_id": current_user.id,
            "receiver_id": receiver_id,
            "content": content,
            "timestamp": message.timestamp.isoformat(),
            "is_read": False,
            "sender_name": f"{current_user.prenom} {current_user.nom}",
            "sender_photo": current_user.photo_profil,
        }

        # Envoyer confirmation à l'expéditeur
        emit("message_sent", message_data)

        # Envoyer le message au destinataire (dans sa room personnelle)
        emit("receive_message", message_data, room=f"user_{receiver_id}")

        # Créer une notification globale pour le destinataire
        try:
            from app.models.notification import Notification

            notif_link = url_for("chat.index")
            Notification.creer_notification(
                user_id=receiver_id,
                titre=f"Nouveau message de {current_user.prenom}",
                message=content[:100] + ("..." if len(content) > 100 else ""),
                type="message",
                link=notif_link,
            )
        except Exception as e:
            print(f"[CHAT ERROR] Failed to create global notification: {e}")

        print(
            f"[CHAT] Message sent: {current_user.nom} -> {receiver.nom} (ID: {message.id})"
        )

    except Exception as e:
        db.session.rollback()
        emit("error", {"message": f"Erreur lors de l'envoi: {str(e)}"})
        print(f"[CHAT ERROR] Error sending message: {e}")


@socketio.on("mark_as_read")
def handle_mark_as_read(data):
    """
    Marque des messages comme lus
    Data attendue:
        - message_ids (list): Liste des IDs de messages à marquer comme lus
        OU
        - conversation_with (int): ID de l'utilisateur dont tous les messages doivent être marqués comme lus
    """
    if not current_user.is_authenticated:
        emit("error", {"message": "Non authentifié"})
        return

    try:
        message_ids = data.get("message_ids", [])
        conversation_with = data.get("conversation_with")

        if message_ids:
            # Marquer des messages spécifiques
            Message.query.filter(
                Message.id.in_(message_ids),
                Message.receiver_id == current_user.id,
                Message.is_read.is_(False),
            ).update({"is_read": True}, synchronize_session=False)

        elif conversation_with:
            # Marquer tous les messages non lus d'une conversation
            Message.query.filter_by(
                sender_id=conversation_with,
                receiver_id=current_user.id,
                is_read=False,
            ).update({"is_read": True}, synchronize_session=False)

        db.session.commit()
        emit("messages_marked_read", {"success": True})

    except Exception as e:
        db.session.rollback()
        emit("error", {"message": f"Erreur: {str(e)}"})


@socketio.on("typing")
def handle_typing(data):
    """
    Gère l'événement de frappe (typing indicator)
    Data attendue:
        - receiver_id (int): ID du destinataire qui doit voir l'indicateur
        - is_typing (bool): True si en train de taper, False sinon
    """
    if not current_user.is_authenticated:
        return

    receiver_id = data.get("receiver_id")
    is_typing = data.get("is_typing", False)

    if receiver_id:
        emit(
            "user_typing",
            {
                "user_id": current_user.id,
                "user_name": f"{current_user.prenom} {current_user.nom}",
                "is_typing": is_typing,
            },
            room=f"user_{receiver_id}",
        )
