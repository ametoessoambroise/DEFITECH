"""
Utils pour la gestion des salles de cours virtuelles
"""

from app.extensions import db
from app.models.videoconference import Room, RoomInvitation, Inscription
from app.models.etudiant import Etudiant
from app.models.enseignant import Enseignant
from app.models.matiere import Matiere
from app.email_utils import send_room_invitation
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def is_course_scheduled_now(course, current_time=None):
    """Vérifie si le cours est prévu à l'heure actuelle"""
    if not current_time:
        current_time = datetime.now()

    current_weekday = current_time.weekday()
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    current_weekday_str = weekdays[current_weekday]

    if not getattr(course, f"jour_{current_weekday_str}", False):
        return False

    course_start = course.heure_debut
    course_end = course.heure_fin
    current_time_only = current_time.time()

    # Marge de 30 minutes avant et 15 minutes après
    start_time = (
        datetime.combine(datetime.today(), course_start) - timedelta(minutes=30)
    ).time()
    end_time = (
        datetime.combine(datetime.today(), course_end) + timedelta(minutes=15)
    ).time()

    return start_time <= current_time_only <= end_time


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

    # Stratégie 1: Étudiants explicitement inscrits via Inscription (plus précis)
    etudiants_inscrits = [
        i.user.etudiant
        for i in Inscription.query.filter_by(course_id=course.id, statut="active").all()
        if i.user and i.user.etudiant
    ]
    app.logger.info(f"Etudiants via Inscription: {len(etudiants_inscrits)}")

    # Stratégie 2: Étudiants via la Filière et l'Année du cours (Robust Fallback)
    # Plus fiable que l'EmploiTemps car ne dépend pas de la planification
    etudiants_filiere = []
    if course and course.filiere and course.annee:
        filiere_nom = course.filiere.nom
        annee = course.annee

        app.logger.info(
            f"Recherche étudiants pour Filière: '{filiere_nom}', Année: '{annee}'"
        )

        # Générer des variations pour l'année pour gérer les incohérences de saisie (accents, formats)
        # Ex: "2ème année" vs "2eme annee" vs "2eme année"
        annees_possibles = [annee]

        # Variations courantes
        replacements = {
            "è": "e",
            "é": "e",
            "1ère": "1ere",
            "1ere": "1ère",
            "ème": "eme",
            "eme": "ème",
            "année": "annee",
            "annee": "année",
        }

        # Créer une variation sans accents / normalisée
        normalized = annee
        for char, repl in replacements.items():
            if char in normalized:
                normalized = normalized.replace(char, repl)

        if normalized not in annees_possibles:
            annees_possibles.append(normalized)

        # Bruteforce des variations communes si ça ressemble à une année standard
        if "1" in annee:
            annees_possibles.extend(["1ère année", "1ere annee", "1ere année"])
        if "2" in annee:
            annees_possibles.extend(
                ["2ème année", "2eme annee", "2eme année", "2ème annee", "2eme annee"]
            )
        if "3" in annee:
            annees_possibles.extend(
                ["3ème année", "3eme annee", "3eme année", "3ème annee"]
            )

        # Dédoublonnage
        annees_possibles = list(set(annees_possibles))

        app.logger.info(
            f"Recherche étudiants pour Filière: '{filiere_nom}', Années possibles: {annees_possibles}"
        )

        etudiants_filiere = Etudiant.query.filter(
            Etudiant.filiere.ilike(filiere_nom),  # Insensible à la casse
            Etudiant.annee.in_(annees_possibles),
        ).all()
    else:
        app.logger.warning(
            "Filière ou Année non définies pour ce cours, recherche par filière impossible"
        )

    app.logger.info(f"Etudiants via Filière/Année: {len(etudiants_filiere)}")

    # Union des deux listes par ID utilisateur pour éviter les doublons
    etudiants_dict = {e.user_id: e for e in etudiants_inscrits if e}
    for e in etudiants_filiere:
        if e and e.user_id not in etudiants_dict:
            etudiants_dict[e.user_id] = e

    inscriptions = list(etudiants_dict.values())
    app.logger.info(f"Total étudiants uniques à inviter: {len(inscriptions)}")

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
