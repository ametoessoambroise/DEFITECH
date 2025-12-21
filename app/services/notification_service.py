"""
Service de notifications pour la communauté
"""

from typing import Optional
from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.models.filiere import Filiere
from app.models.post import Post


class NotificationService:
    """Service centralisé pour la gestion des notifications"""
    
    @staticmethod
    def notify_filiere_subscribers(
        filiere_id: int,
        title: str,
        message: str,
        link: Optional[str] = None,
        exclude_user_id: Optional[int] = None,
        element_id: Optional[int] = None,
        element_type: Optional[str] = None
    ) -> int:
        """
        Notifie tous les utilisateurs abonnés à une filière
        
        Args:
            filiere_id: ID de la filière
            title: Titre de la notification
            message: Message de la notification
            link: Lien vers l'élément concerné (optionnel)
            exclude_user_id: ID de l'utilisateur à exclure (optionnel)
            element_id: ID de l'élément lié (optionnel)
            element_type: Type de l'élément lié (optionnel)
            
        Returns:
            Nombre de notifications envoyées
        """
        try:
            # Récupérer la filière
            filiere = Filiere.query.get(filiere_id)
            if not filiere:
                return 0
            
            notifications_count = 0
            
            # Notifier tous les étudiants de la filière
            etudiants = User.query.filter_by(role="etudiant").join(
                User.etudiant
            ).filter(
                User.etudiant.any(filiere=filiere.nom)
            ).all()
            
            for etudiant in etudiants:
                if exclude_user_id and etudiant.id == exclude_user_id:
                    continue
                    
                notification = Notification(
                    user_id=etudiant.id,
                    titre=title,
                    message=message,
                    type="post",
                    element_id=element_id,
                    element_type=element_type,
                    link=link
                )
                db.session.add(notification)
                notifications_count += 1
            
            # Notifier les enseignants administrateurs de la filière
            from app.models.filiere import FiliereAdmin
            admins = FiliereAdmin.query.filter_by(filiere_id=filiere_id).all()
            
            for admin in admins:
                if exclude_user_id and admin.enseignant.user_id == exclude_user_id:
                    continue
                    
                notification = Notification(
                    user_id=admin.enseignant.user_id,
                    titre=title,
                    message=message,
                    type="post",
                    element_id=element_id,
                    element_type=element_type,
                    link=link
                )
                db.session.add(notification)
                notifications_count += 1
            
            # Notifier les administrateurs globaux
            admin_users = User.query.filter_by(role="admin").all()
            
            for admin_user in admin_users:
                if exclude_user_id and admin_user.id == exclude_user_id:
                    continue
                    
                notification = Notification(
                    user_id=admin_user.id,
                    titre=title,
                    message=message,
                    type="post",
                    element_id=element_id,
                    element_type=element_type,
                    link=link
                )
                db.session.add(notification)
                notifications_count += 1
            
            db.session.commit()
            return notifications_count
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def notify_post_author(
        post_id: int,
        commenter_id: int,
        commenter_name: str,
        post_title: str
    ) -> bool:
        """
        Notifie l'auteur d'un post lorsqu'il reçoit un commentaire
        
        Args:
            post_id: ID du post
            commenter_id: ID de l'utilisateur qui commente
            commenter_name: Nom de l'utilisateur qui commente
            post_title: Titre du post
            
        Returns:
            True si la notification a été envoyée, False sinon
        """
        try:
            post = Post.query.get(post_id)
            if not post or post.auteur_id == commenter_id:
                return False  # Ne pas notifier l'auteur lui-même
            
            notification = Notification(
                user_id=post.auteur_id,
                titre="Nouveau commentaire",
                message=f"{commenter_name} a commenté votre publication: {post_title}",
                type="comment",
                element_id=post_id,
                element_type="post",
                link=f"/community/post/{post_id}"
            )
            
            db.session.add(notification)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def notify_post_update(
        post_id: int,
        author_name: str,
        post_title: str
    ) -> bool:
        """
        Notifie les abonnés lorsqu'un post est mis à jour
        
        Args:
            post_id: ID du post
            author_name: Nom de l'auteur
            post_title: Titre du post
            
        Returns:
            True si la notification a été envoyée, False sinon
        """
        try:
            post = Post.query.get(post_id)
            if not post:
                return False
            
            title = "Mise à jour de publication"
            message = f"{author_name} a mis à jour sa publication: {post_title}"
            link = f"/community/post/{post_id}"
            
            count = NotificationService.notify_filiere_subscribers(
                filiere_id=post.filiere_id,
                title=title,
                message=message,
                link=link,
                exclude_user_id=post.auteur_id,
                element_id=post_id,
                element_type="post"
            )
            
            return count > 0
            
        except Exception as e:
            raise e
    
    @staticmethod
    def notify_new_post(
        post_id: int,
        author_name: str,
        post_title: str
    ) -> int:
        """
        Notifie les abonnés lorsqu'un nouveau post est créé
        
        Args:
            post_id: ID du post
            author_name: Nom de l'auteur
            post_title: Titre du post
            
        Returns:
            Nombre de notifications envoyées
        """
        try:
            post = Post.query.get(post_id)
            if not post:
                return 0
            
            title = f"Nouveau post dans {post.filiere.nom}"
            message = f"{author_name} a publié un nouveau post : {post_title[:50]}..."
            link = f"/community/post/{post_id}"
            
            return NotificationService.notify_filiere_subscribers(
                filiere_id=post.filiere_id,
                title=title,
                message=message,
                link=link,
                exclude_user_id=post.auteur_id,
                element_id=post_id,
                element_type="post"
            )
            
        except Exception as e:
            raise e
