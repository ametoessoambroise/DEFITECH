"""
Utils pour la gestion des salles de cours virtuelles
"""

from app.extensions import db
from app.models.videoconference import Room, RoomInvitation
from app.models.etudiant import Etudiant
from app.models.enseignant import Enseignant
from app.models.matiere import Matiere
from app.models.emploi_temps import EmploiTemps
from app.models.filiere import Filiere
from app.email_utils import send_room_invitation
from datetime import datetime


def send_room_invitations(room_id, app):
    """
    Envoie des invitations par email à tous les étudiants inscrits au cours

    Args:
        room_id (int): ID de la salle de cours
        app: Instance de l'application Flask

    Returns:
        dict: Résultat de l'opération avec le nombre d'invitations envoyées et d'erreurs
    """
    # Récupérer la salle et les informations associées
    room = Room.query.get(room_id)
    if not room:
        return {
            "success": False,
            "message": "Salle de cours introuvable",
            "sent": 0,
            "errors": 0,
        }

    # Récupérer le cours et l'enseignant
    course = Matiere.query.get(room.course_id) if room.course_id else None

    # Pour l'enseignant, on cherche d'abord par user_id puis par enseignant_id
    enseignant = None
    if room.host_id:
        # Essayer de trouver l'enseignant par user_id (cas le plus probable)
        enseignant = Enseignant.query.filter_by(user_id=room.host_id).first()
        # Si pas trouvé, essayer par enseignant_id direct
        if not enseignant:
            enseignant = Enseignant.query.get(room.host_id)

    app.logger.info(
        f"Room ID: {room_id}, Course ID: {room.course_id}, Host ID: {room.host_id}"
    )
    app.logger.info(
        f"Course found: {course is not None}, Enseignant found: {enseignant is not None}"
    )

    if course:
        app.logger.info(f"Course details: {course.nom} (ID: {course.id})")
    else:
        app.logger.warning(f"Course with ID {room.course_id} not found in database")

    if enseignant:
        app.logger.info(
            f"Enseignant details: {enseignant.user.prenom} {enseignant.user.nom} (ID: {enseignant.id})"
        )
    else:
        app.logger.warning(
            f"Enseignant with Host ID {room.host_id} not found in database"
        )

    # Si le cours ou l'enseignant n'est pas trouvé, on continue quand même avec les étudiants
    # mais on enregistre un avertissement
    if not course or not enseignant:
        app.logger.warning(
            "Cours ou enseignant introuvable, mais tentative d'envoyer les invitations aux étudiants"
        )
        # On ne retourne pas d'erreur ici, on continue avec les étudiants si possible

        # Si pas de cours, on ne peut pas trouver les étudiants via EmploiTemps
        if not course:
            app.logger.warning("Impossible de trouver les étudiants sans cours valide")
            return {
                "success": False,
                "message": "Cours introuvable - impossible de déterminer les étudiants à inviter",
                "sent": 0,
                "errors": 0,
            }

    # Récupérer les étudiants ayant cette matière dans leur emploi du temps
    app.logger.info(f"Recherche des étudiants pour le cours ID: {course.id}")

    # D'abord, on récupère les filières qui ont cette matière dans leur emploi du temps
    filieres_avec_matiere = [
        f[0]
        for f in db.session.query(EmploiTemps.filiere_id)
        .filter(EmploiTemps.matiere_id == course.id)
        .distinct()
        .all()
    ]

    app.logger.info(f"Filières avec cette matière: {filieres_avec_matiere}")

    # Ensuite, on récupère les noms des filières
    if filieres_avec_matiere:
        noms_filieres = [
            f[0]
            for f in db.session.query(Filiere.nom)
            .filter(Filiere.id.in_(filieres_avec_matiere))
            .all()
        ]
        app.logger.info(f"Noms des filières: {noms_filieres}")

        # Enfin, on récupère les étudiants de ces filières par nom
        if noms_filieres:
            etudiants = (
                db.session.query(Etudiant)
                .filter(Etudiant.filiere.in_(noms_filieres))
                .all()
            )
        else:
            etudiants = []
            app.logger.warning("Aucun nom de filière trouvé pour les IDs fournis")
    else:
        etudiants = []
        app.logger.warning(
            "Aucune filière trouvée avec cette matière dans l'emploi du temps"
        )

    app.logger.info(f"Nombre d'étudiants trouvés via emploi du temps: {len(etudiants)}")
    if etudiants:
        app.logger.info(
            f"Premier étudiant: {etudiants[0].user.email if etudiants[0].user else 'Pas d\'email'}"
        )

    inscriptions = etudiants  # Pour maintenir la compatibilité avec le reste du code

    sent_count = 0
    error_count = 0

    # Envoyer une invitation à chaque étudiant
    for etudiant in inscriptions:
        try:
            # Créer une entrée dans la table des invitations
            invitation = RoomInvitation(
                room_id=room.id,
                user_id=etudiant.user_id,
                status="sent",
                sent_at=datetime.utcnow(),
            )
            db.session.add(invitation)

            # Envoyer l'email
            send_room_invitation(etudiant, enseignant, course, room.room_token, app)

            sent_count += 1

        except Exception as e:
            error_count += 1
            # Mettre à jour l'invitation en cas d'erreur
            if "invitation" in locals():
                invitation.status = "error"
                invitation.error_message = str(e)
            app.logger.error(
                f"Erreur lors de l'envoi de l'invitation à {etudiant.user.email}: {str(e)}"
            )

    # Valider les changements en base de données
    try:
        db.session.commit()
        return {
            "success": True,
            "message": f"{sent_count} invitations envoyées avec succès",
            "sent": sent_count,
            "errors": error_count,
        }
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erreur lors de la validation des invitations: {str(e)}")
        return {
            "success": False,
            "message": f"Erreur lors de l'enregistrement des invitations: {str(e)}",
            "sent": sent_count,
            "errors": error_count,
        }
