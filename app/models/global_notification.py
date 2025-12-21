from datetime import datetime, timedelta
from app.extensions import db


class GlobalNotification(db.Model):
    """Modèle pour les notifications globales du site"""

    __tablename__ = "global_notification"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(
        db.String(20), nullable=False, default="info"
    )  # info, warning, error, success
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_expiration = db.Column(db.DateTime, nullable=True)
    est_active = db.Column(db.Boolean, default=True, nullable=False)
    priorite = db.Column(
        db.Integer, default=1, nullable=False
    )  # 1=faible, 2=moyen, 3=élevé, 4=critique
    createur_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Relations
    createur = db.relationship(
        "User", backref=db.backref("global_notifications", lazy=True)
    )

    def __repr__(self):
        return f"<GlobalNotification {self.id} - {self.titre[:50]}>"

    @property
    def est_expiree(self):
        """Vérifie si la notification est expirée"""
        if self.date_expiration:
            return datetime.utcnow() > self.date_expiration
        return False

    @property
    def type_css_class(self):
        """Retourne la classe CSS selon le type de notification"""
        classes = {
            "info": "bg-blue-50 border-blue-200 text-blue-800",
            "warning": "bg-yellow-50 border-yellow-200 text-yellow-800",
            "error": "bg-red-50 border-red-200 text-red-800",
            "success": "bg-green-50 border-green-200 text-green-800",
        }
        return classes.get(self.type, classes["info"])

    @property
    def type_icon(self):
        """Retourne l'icône selon le type de notification"""
        icons = {
            "info": "fas fa-info-circle",
            "warning": "fas fa-exclamation-triangle",
            "error": "fas fa-times-circle",
            "success": "fas fa-check-circle",
        }
        return icons.get(self.type, icons["info"])

    @property
    def priorite_css_class(self):
        """Retourne la classe CSS selon la priorité"""
        classes = {
            1: "border-l-4 border-l-blue-400",
            2: "border-l-4 border-l-yellow-400",
            3: "border-l-4 border-l-orange-400",
            4: "border-l-4 border-l-red-400",
        }
        return classes.get(self.priorite, classes[1])

    @classmethod
    def get_notifications_actives(cls):
        """Récupère toutes les notifications actives et non expirées"""
        try:
            return (
                cls.query.filter_by(est_active=True)
                .filter(
                    db.or_(
                        cls.date_expiration.is_(None),
                        cls.date_expiration > datetime.utcnow(),
                    )
                )
                .order_by(cls.priorite.desc(), cls.date_creation.desc())
                .all()
            )
        except Exception as e:
            # En cas d'erreur de transaction, retourner une liste vide
            print(f"Erreur lors de la récupération des notifications: {e}")
            db.session.rollback()
            return []

    @classmethod
    def create_notification(
        cls,
        titre,
        message,
        type="info",
        duree_heures=None,
        priorite=1,
        createur_id=None,
    ):
        """Crée une nouvelle notification globale et envoie des emails"""
        notification = cls(
            titre=titre,
            message=message,
            type=type,
            priorite=priorite,
            createur_id=createur_id,
        )

        # Définir la date d'expiration si une durée est spécifiée
        if duree_heures:
            notification.date_expiration = datetime.utcnow() + timedelta(
                hours=duree_heures
            )

        db.session.add(notification)
        db.session.commit()

        # Envoyer des emails aux utilisateurs actifs
        try:
            from app.models.user import User
            from email_utils import send_bulk_notification_email

            # Récupérer tous les utilisateurs actifs (approuvés et non supprimés)
            users = User.query.filter_by(statut="approuve", is_active=True).all()

            if users:
                # Envoyer les emails en arrière-plan
                success_count, failed_count = send_bulk_notification_email(
                    users, notification
                )

                # Log the results
                if success_count > 0:
                    print(
                        f"✅ Emails de notification envoyés à {success_count} utilisateurs"
                    )
                if failed_count > 0:
                    print(f"❌ Échec d'envoi d'emails à {failed_count} utilisateurs")

        except Exception as e:
            print(f"⚠️ Erreur lors de l'envoi des emails de notification: {e}")

        return notification

    def marquer_comme_lue(self, user_id=None):
        """Marque la notification comme lue par un utilisateur"""
        # Pour l'instant, on ne stocke pas les lectures individuelles
        # Mais on peut étendre plus tard si nécessaire
        pass

    def desactiver(self):
        """Désactive la notification"""
        self.est_active = False
        db.session.commit()
