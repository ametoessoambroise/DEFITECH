"""
Gestion des événements Socket.IO pour la visioconférence - VERSION CORRIGÉE
"""

from flask import request
from flask_socketio import join_room, leave_room, emit
from datetime import datetime, timedelta
from app.models.videoconference import Room, RoomParticipant, RoomActivityLog
from app.extensions import db
from app.models.user import User
import logging
from threading import Timer

# Importer CSRF pour l'exemption
try:
    from app.extensions import csrf

    CSRF_AVAILABLE = True
except ImportError:
    CSRF_AVAILABLE = False
    csrf = None

logger = logging.getLogger(__name__)

# Dictionnaire pour stocker la correspondance user_id -> socket_id avec timestamp
user_socket_map = {}  # {user_id: {"socket_id": socket_id, "timestamp": datetime}}


def csrf_exempt_socketio_handler(f):
    """Désactive la protection CSRF pour les handlers Socket.IO."""
    if CSRF_AVAILABLE and csrf:
        csrf.exempt(f)
    return f


def verify_user_in_room(user_id, room_token):
    """
    Vérifie si un utilisateur est bien dans la salle spécifiée.
    Retourne True si l'utilisateur est dans la salle, False sinon.
    """
    try:
        # Vérifier si la salle existe
        room = Room.query.filter_by(room_token=room_token).first()
        if not room:
            logger.warning(f"🚫 Salle {room_token} non trouvée")
            return False

        # Vérifier si l'utilisateur est dans la salle
        participant = RoomParticipant.query.filter_by(
            room_id=room.id, user_id=int(user_id)
        ).first()

        if not participant:
            logger.warning(
                f"🚫 Utilisateur {user_id} non trouvé dans la salle {room_token}"
            )
            return False

        # Vérifier si l'utilisateur est toujours actif
        if participant.left_at is not None:
            logger.warning(f"🚫 Utilisateur {user_id} a quitté la salle {room_token}")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification de permissions: {e}")
        return False


def get_user_room_from_socket(socket_id):
    """
    Récupère la salle d'un utilisateur à partir de son socket ID.
    Retourne le room_token ou None si non trouvé.
    """
    try:
        # Chercher l'utilisateur par socket ID
        for user_id, mapping in user_socket_map.items():
            if mapping["socket_id"] == socket_id:
                # Récupérer la salle active de cet utilisateur
                participant = RoomParticipant.query.filter_by(
                    user_id=int(user_id), left_at=None
                ).first()

                if participant:
                    room = Room.query.get(participant.room_id)
                    if room:
                        return room.room_token

        return None

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération de la salle: {e}")
        return None


def cleanup_stale_mappings():
    """Nettoie les mappings de plus de 5 minutes."""
    current_time = datetime.utcnow()
    stale_users = []

    for user_id, mapping in user_socket_map.items():
        if current_time - mapping["timestamp"] > timedelta(minutes=5):
            stale_users.append(user_id)

    for user_id in stale_users:
        logger.info(f"🗑️ Suppression mapping obsolète pour user_id {user_id}")
        del user_socket_map[user_id]

    logger.info(f"🧹 Nettoyage terminé. {len(stale_users)} mappings supprimés")


def schedule_cleanup():
    """Programme le prochain nettoyage dans 5 minutes."""
    Timer(300.0, cleanup_stale_mappings).start()  # 300 secondes = 5 minutes
    Timer(300.0, schedule_cleanup).start()  # Programme le prochain nettoyage


# Démarrer le nettoyage automatique
schedule_cleanup()


def register_socketio_handlers(socket_io):
    """Enregistre les gestionnaires d'événements Socket.IO."""

    @csrf_exempt_socketio_handler
    @socket_io.on("connect")
    def handle_connect():
        """Gère la connexion d'un client Socket.IO."""
        logger.info(f"✅ Client connecté: {request.sid}")
        print(f"✅ Client connecté: {request.sid}")

    @csrf_exempt_socketio_handler
    @socket_io.on("disconnect")
    def handle_disconnect():
        """Gère la déconnexion d'un client Socket.IO."""
        logger.info(f"❌ Client déconnecté: {request.sid}")
        print(f"❌ Client déconnecté: {request.sid}")

        # Retirer l'utilisateur de la carte
        user_id_to_remove = None
        for user_id, mapping in user_socket_map.items():
            if mapping["socket_id"] == request.sid:
                user_id_to_remove = user_id
                break

        if user_id_to_remove:
            logger.info(f"🗑️ Suppression mapping user_id {user_id_to_remove}")
            del user_socket_map[user_id_to_remove]

    @csrf_exempt_socketio_handler
    @socket_io.on("join_room")
    def handle_join_room(data):
        """
        Gère la connexion d'un utilisateur à une salle de visioconférence.
        """
        room_token = data.get("room_token")
        user_id = data.get("user_id")
        username = data.get("username")

        logger.info(f"📥 join_room reçu - room: {room_token}, user: {user_id}")

        if not room_token or not user_id:
            logger.error("❌ Paramètres manquants")
            emit("error", {"message": "Paramètres manquants"})
            return

        # Vérifier que l'utilisateur a le droit de rejoindre la salle
        user = User.query.get(user_id)
        room = Room.query.filter_by(room_token=room_token).first()

        if not user or not room:
            logger.error("❌ Salle ou utilisateur non trouvé")
            emit("error", {"message": "Salle ou utilisateur non trouvé"})
            return

        # Rejoindre la room Socket.IO
        join_room(room_token)
        logger.info(f"✅ {username} rejoint la room Socket.IO: {room_token}")

        # Stocker la correspondance user_id -> socket_id avec timestamp
        user_socket_map[str(user_id)] = {
            "socket_id": request.sid,
            "timestamp": datetime.utcnow(),
        }  # Convertir en string pour cohérence
        logger.info(f"🗺️ Mapping: user_id {user_id} -> socket_id {request.sid}")
        logger.info(f"📊 Mappings actuels: {user_socket_map}")

        # Récupérer ou créer la participation
        participant = RoomParticipant.query.filter_by(
            room_id=room.id, user_id=user.id
        ).first()

        if participant:
            participant.joined_at = datetime.utcnow()
            participant.left_at = None
        else:
            participant = RoomParticipant(
                room_id=room.id,
                user_id=user.id,
                role="participant",
            )
            db.session.add(participant)

        # Enregistrer l'activité
        activity = RoomActivityLog(
            room_id=room.id,
            user_id=user.id,
            action="joined",
            details=f"A rejoint la salle {room.name}",
        )
        db.session.add(activity)
        db.session.commit()

        # Informer les autres participants (SAUF le nouveau venu)
        logger.info(
            f"📣 Broadcast user_joined à la room {room_token} (skip {request.sid})"
        )
        emit(
            "user_joined",
            {
                "user_id": str(user.id),  # String pour cohérence
                "username": username or f"{user.prenom} {user.nom}",
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=room_token,
            skip_sid=request.sid,  # Ne pas envoyer à soi-même
        )

        # Envoyer la liste des participants actuels au nouveau venu
        participants = RoomParticipant.query.filter_by(
            room_id=room.id, left_at=None
        ).all()

        participant_list = [
            {
                "id": str(p.user.id),
                "username": f"{p.user.prenom} {p.user.nom}",
                "role": p.role,
                "is_you": p.user_id == user.id,
            }
            for p in participants
        ]

        logger.info(f"📋 Envoi room_info avec {len(participant_list)} participants")
        emit(
            "room_info",
            {
                "room": {"id": room.id, "name": room.name, "token": room.room_token},
                "participants": participant_list,
            },
            room=room_token,  # Envoyer à tous les participants de la room
        )

    @csrf_exempt_socketio_handler
    @socket_io.on("leave_room")
    def handle_leave_room(data):
        """Gère la déconnexion d'un utilisateur d'une salle."""
        room_token = data.get("room_token")
        user_id = data.get("user_id")

        logger.info(f"👋 leave_room - room: {room_token}, user: {user_id}")

        if not room_token or not user_id:
            return

        # Quitter la room Socket.IO
        leave_room(room_token)

        # Mettre à jour la participation
        room = Room.query.filter_by(room_token=room_token).first()
        if not room:
            return

        participant = RoomParticipant.query.filter_by(
            room_id=room.id, user_id=user_id, left_at=None
        ).first()

        if participant:
            participant.left_at = datetime.utcnow()

            activity = RoomActivityLog(
                room_id=room.id,
                user_id=user_id,
                action="left",
                details=f"A quitté la salle {room.name}",
            )
            db.session.add(activity)
            db.session.commit()

            # Informer les autres participants
            emit(
                "user_left",
                {"user_id": str(user_id), "timestamp": datetime.utcnow().isoformat()},
                room=room_token,
            )

        # Nettoyer le mapping
        if str(user_id) in user_socket_map:
            del user_socket_map[str(user_id)]

    @csrf_exempt_socketio_handler
    @socket_io.on("offer")
    def handle_offer(data):
        """
        Transmet une offre WebRTC à un utilisateur spécifique.
        """
        to_user_id = str(data.get("to"))
        from_user_id = str(data.get("from"))
        offer = data.get("offer")

        logger.info(f"📨 Offre reçue de {from_user_id} vers {to_user_id}")
        logger.info(f"🗺️ Mappings disponibles: {user_socket_map.keys()}")

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que l'émetteur est dans une salle
        sender_room = get_user_room_from_socket(request.sid)
        if not sender_room:
            logger.error(f"🚫 Utilisateur {from_user_id} n'est dans aucune salle")
            return

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que le destinataire est dans la même salle
        if not verify_user_in_room(to_user_id, sender_room):
            logger.error(
                f"🚫 Utilisateur {to_user_id} n'est pas dans la salle {sender_room}"
            )
            return

        # Récupérer le socket ID du destinataire
        to_mapping = user_socket_map.get(to_user_id)
        to_socket_id = to_mapping["socket_id"] if to_mapping else None

        if to_socket_id:
            logger.info(
                f"✅ Envoi offre au socket {to_socket_id} (vérifié: même salle {sender_room})"
            )
            emit("offer", {"from": from_user_id, "offer": offer}, room=to_socket_id)
        else:
            logger.error(f"❌ Socket ID non trouvé pour user {to_user_id}")
            logger.error(f"📊 Mappings disponibles: {list(user_socket_map.items())}")

    @csrf_exempt_socketio_handler
    @socket_io.on("answer")
    def handle_answer(data):
        """Transmet une réponse WebRTC à un utilisateur spécifique."""
        to_user_id = str(data.get("to"))
        from_user_id = str(data.get("from"))
        answer = data.get("answer")

        logger.info(f"📨 Réponse reçue de {from_user_id} vers {to_user_id}")

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que l'émetteur est dans une salle
        sender_room = get_user_room_from_socket(request.sid)
        if not sender_room:
            logger.error(f"🚫 Utilisateur {from_user_id} n'est dans aucune salle")
            return

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que le destinataire est dans la même salle
        if not verify_user_in_room(to_user_id, sender_room):
            logger.error(
                f"🚫 Utilisateur {to_user_id} n'est pas dans la salle {sender_room}"
            )
            return

        to_mapping = user_socket_map.get(to_user_id)
        to_socket_id = to_mapping["socket_id"] if to_mapping else None

        if to_socket_id:
            logger.info(
                f"✅ Envoi réponse au socket {to_socket_id} (vérifié: même salle {sender_room})"
            )
            emit("answer", {"from": from_user_id, "answer": answer}, room=to_socket_id)
        else:
            logger.error(f"❌ Socket ID non trouvé pour user {to_user_id}")

    @csrf_exempt_socketio_handler
    @socket_io.on("ice_candidate")
    def handle_ice_candidate(data):
        """Transmet les candidats ICE entre pairs."""
        to_user_id = str(data.get("to"))
        from_user_id = str(data.get("from"))
        candidate = data.get("candidate")

        logger.debug(f"🧊 ICE candidate de {from_user_id} vers {to_user_id}")

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que l'émetteur est dans une salle
        sender_room = get_user_room_from_socket(request.sid)
        if not sender_room:
            logger.error(f"🚫 Utilisateur {from_user_id} n'est dans aucune salle")
            return

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que le destinataire est dans la même salle
        if not verify_user_in_room(to_user_id, sender_room):
            logger.error(
                f"🚫 Utilisateur {to_user_id} n'est pas dans la salle {sender_room}"
            )
            return

        to_mapping = user_socket_map.get(to_user_id)
        to_socket_id = to_mapping["socket_id"] if to_mapping else None

        if to_socket_id:
            logger.debug(
                f"✅ Envoi ICE candidate au socket {to_socket_id} (vérifié: même salle {sender_room})"
            )
            emit(
                "ice_candidate",
                {"from": from_user_id, "candidate": candidate},
                room=to_socket_id,
            )
        else:
            logger.warning(
                f"⚠️ Socket ID non trouvé pour ICE candidate vers {to_user_id}"
            )

    @csrf_exempt_socketio_handler
    @socket_io.on("toggle_audio")
    def handle_toggle_audio(data):
        """Gère le changement d'état du microphone."""
        room_token = data.get("room_token")
        user_id = str(data.get("user_id"))
        is_muted = data.get("is_muted")

        logger.info(f"🎤 Toggle audio - user: {user_id}, muted: {is_muted}")

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que l'utilisateur est dans la salle spécifiée
        if not verify_user_in_room(user_id, room_token):
            logger.error(
                f"🚫 Utilisateur {user_id} n'est pas dans la salle {room_token}"
            )
            return

        if room_token:
            emit(
                "user_audio_changed",
                {"user_id": user_id, "is_muted": is_muted},
                room=room_token,
                skip_sid=request.sid,
            )

    @csrf_exempt_socketio_handler
    @socket_io.on("toggle_video")
    def handle_toggle_video(data):
        """Gère le changement d'état de la caméra."""
        room_token = data.get("room_token")
        user_id = str(data.get("user_id"))
        is_off = data.get("is_off")

        logger.info(f"📹 Toggle vidéo - user: {user_id}, off: {is_off}")

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que l'utilisateur est dans la salle spécifiée
        if not verify_user_in_room(user_id, room_token):
            logger.error(
                f"🚫 Utilisateur {user_id} n'est pas dans la salle {room_token}"
            )
            return

        if room_token:
            emit(
                "user_video_changed",
                {"user_id": user_id, "is_off": is_off},
                room=room_token,
                skip_sid=request.sid,
            )

    @csrf_exempt_socketio_handler
    @socket_io.on("chat_message")
    def handle_chat_message(data):
        """Gère l'envoi d'un message dans le chat."""
        room_token = data.get("room_token")
        user_id = data.get("user_id")
        message = data.get("message")

        logger.info(f"💬 Message chat de {user_id}: {message}")

        # 🔐 VÉRIFICATION DE SÉCURITÉ : Vérifier que l'utilisateur est dans la salle spécifiée
        if not verify_user_in_room(user_id, room_token):
            logger.error(
                f"🚫 Utilisateur {user_id} n'est pas dans la salle {room_token}"
            )
            return

        if room_token:
            room = Room.query.filter_by(room_token=room_token).first()
            if room:
                # Enregistrer le message
                activity = RoomActivityLog(
                    room_id=room.id,
                    user_id=user_id,
                    action="chat_message",
                    details=message,
                )
                db.session.add(activity)
                db.session.commit()

                # Diffuser le message
                emit(
                    "new_chat_message",
                    {
                        "user_id": str(user_id),
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    room=room_token,
                )

    @csrf_exempt_socketio_handler
    @socket_io.on("screen_share_started")
    def handle_screen_share_started(data):
        """Gère le début du partage d'écran."""
        room_token = data.get("room_token")
        user_id = data.get("user_id")
        username = data.get("username")

        logger.info(f"📺 Screen share STARTED - user: {user_id}")

        if not verify_user_in_room(user_id, room_token):
            return

        emit(
            "screen_share_started",
            {"user_id": str(user_id), "username": username},
            room=room_token,
            skip_sid=request.sid,
        )

    @csrf_exempt_socketio_handler
    @socket_io.on("screen_share_stopped")
    def handle_screen_share_stopped(data):
        """Gère la fin du partage d'écran."""
        room_token = data.get("room_token")
        user_id = data.get("user_id")

        logger.info(f"📺 Screen share STOPPED - user: {user_id}")

        if not verify_user_in_room(user_id, room_token):
            return

        emit(
            "screen_share_stopped",
            {"user_id": str(user_id)},
            room=room_token,
            skip_sid=request.sid,
        )
