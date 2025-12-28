from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
    abort,
    send_from_directory,
)
from flask_login import login_required, current_user
import os
from datetime import datetime
from functools import wraps
import json

# Utilisation de current_app pour accéder à db
from app.extensions import db

from app.services.notification_service import NotificationService

# Création du blueprint
community_bp = Blueprint("community", __name__, url_prefix="/community")


def filiere_admin_required(f):
    """Décorateur pour vérifier si l'utilisateur est admin de la filière"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Imports locaux pour éviter les imports circulaires
        from app.models.filiere import FiliereAdmin
        from app.models.post import Post

        filiere_id = kwargs.get("filiere_id")
        if not filiere_id:
            post_id = kwargs.get("post_id")
            if post_id:
                post = db.session.get(Post, post_id) or db.session.query(
                    Post
                ).get_or_404(post_id)
                filiere_id = post.filiere_id
            else:
                abort(404)

        is_admin = False
        if current_user.role == "admin":
            is_admin = True
        elif hasattr(current_user, "enseignant") and current_user.enseignant:
            is_admin = (
                db.session.query(FiliereAdmin)
                .filter_by(
                    filiere_id=filiere_id, enseignant_id=current_user.enseignant.id
                )
                .first()
                is not None
            )

        if not is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@community_bp.route("/")
@login_required
def index():
    """
    Page d'accueil de la communauté.

    Cette fonction est l'endpoint de la route principale de la communauté.
    Elle est appelée lorsque l'utilisateur accède à la page d'accueil de la communauté.

    Returns:
        Response: La réponse HTTP contenant la page d'accueil de la communauté.
    """
    from models.filiere import Filiere, FiliereAdmin

    # Récupérer les filières auxquelles l'utilisateur a accès
    if current_user.role == "admin":
        filieres = Filiere.query.all()
    elif current_user.role == "enseignant":
        filieres = (
            Filiere.query.join(FiliereAdmin, Filiere.id == FiliereAdmin.filiere_id)
            .filter(FiliereAdmin.enseignant_id == current_user.enseignant.id)
            .all()
        )
    else:  # Étudiant
        filieres = Filiere.query.filter_by(nom=current_user.etudiant.filiere).all()

    # Si l'utilisateur n'a qu'une seule filière, rediriger directement vers celle-ci
    if len(filieres) == 1:
        return redirect(url_for("community.filiale", filiere_id=filieres[0].id))

    return render_template("community/list_posts.html", filieres=filieres)


@community_bp.route("/filiere/<int:filiere_id>")
@login_required
def filiale(filiere_id):
    """
    Affiche les publications d'une filière spécifique.

    Cette fonction est l'endpoint de la route '/filiere/{filiere_id}'.
    Elle est appelée lorsque l'utilisateur accède à la page des publications d'une filière spécifique.

    Paramètres:
        - filiere_id (int): L'ID de la filière pour laquelle afficher les publications.

    Retourne:
        Response: La réponse HTTP contenant la page des publications de la filière spécifiée.
    """
    from models.filiere import Filiere, FiliereAdmin
    from models.post import Post

    filiere = Filiere.query.get_or_404(filiere_id)

    # Vérifier les permissions d'accès
    if current_user.role == "etudiant" and filiere.nom != current_user.etudiant.filiere:
        abort(403)
    elif current_user.role == "enseignant" and not any(
        fa.filiere_id == filiere_id for fa in current_user.enseignant.filieres_admin
    ):
        abort(403)

    # Récupérer les paramètres de pagination et de tri
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "newest")
    search = request.args.get("q", "")

    # Construire la requête de base
    query = Post.query.filter_by(filiere_id=filiere_id)

    # Appliquer la recherche si nécessaire
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Post.titre.ilike(search_term)) | (Post.contenu.ilike(search_term))
        )

    # Appliquer le tri
    if sort == "popular":
        # Note: Vous devrez peut-être ajouter un compteur de vues pour un tri précis par popularité
        query = query.order_by(Post.est_epingle.desc(), Post.date_creation.desc())
    else:  # newest par défaut
        query = query.order_by(Post.est_epingle.desc(), Post.date_creation.desc())

    # Pagination
    posts = query.paginate(page=page, per_page=10, error_out=False)

    # Récupérer toutes les filières pour le menu latéral
    if current_user.role == "admin":
        filieres = Filiere.query.all()
    elif current_user.role == "enseignant":
        filieres = (
            Filiere.query.join(FiliereAdmin, Filiere.id == FiliereAdmin.filiere_id)
            .filter(FiliereAdmin.enseignant_id == current_user.enseignant.id)
            .all()
        )
    else:  # Étudiant
        filieres = Filiere.query.filter_by(nom=current_user.etudiant.filiere).all()

    return render_template(
        "community/list_posts.html",
        filiere=filiere,
        filieres=filieres,
        posts=posts,
        current_sort=sort,
        current_search=search,
    )


@community_bp.route("/post/<int:post_id>")
@login_required
def view_post(post_id):
    """
    Affiche un post et ses commentaires.

    Cette fonction est l'endpoint de la route '/post/{post_id}'.
    Elle est appelée lorsque l'utilisateur accède à la page d'un post spécifique avec ses commentaires.

    Paramètres:
        - post_id (int): L'ID du post à afficher.

    Retourne:
        Response: La réponse HTTP contenant la page du post spécifié avec ses commentaires.
    """
    from models.post import Post
    from models.commentaire import Commentaire
    from sqlalchemy.orm import joinedload

    post = Post.query.options(joinedload(Post.auteur)).get_or_404(post_id)

    # Vérifier les permissions d'accès
    if (
        current_user.role == "etudiant"
        and post.filiere.nom != current_user.etudiant.filiere
    ):
        abort(403)

    # Incrémenter le compteur de vues
    post.vues = (post.vues or 0) + 1
    db.session.commit()

    # Récupérer les commentaires triés par date
    commentaires = (
        Commentaire.query.filter_by(post_id=post_id)
        .order_by(Commentaire.date_creation.asc())
        .all()
    )

    return render_template(
        "community/view_post.html",
        post=post,
        commentaires=commentaires,
        filiere=post.filiere,
    )


@community_bp.route("/post/nouveau/<int:filiere_id>", methods=["GET", "POST"])
@login_required
def create_post(filiere_id):
    """
    Créer un nouveau post.

    Cette fonction est l'endpoint de la route '/post/nouveau/{filiere_id}'.
    Elle est appelée lorsque l'utilisateur souhaite créer un nouveau post pour la filière spécifiée.

    Paramètres:
        - filiere_id (int): L'ID de la filière pour laquelle créer le post.

    Retourne:
        Response: La réponse HTTP contenant la page de création de post pour la filière spécifiée.
    """
    from models.filiere import Filiere
    from models.post import Post
    from models.piece_jointe import PieceJointe

    filiere = Filiere.query.get_or_404(filiere_id)

    # Vérifier les permissions
    if current_user.role == "etudiant" and filiere.nom != current_user.etudiant.filiere:
        abort(403)

    if request.method == "POST":
        titre = request.form.get("titre", "").strip()
        contenu = request.form.get("contenu", "").strip()

        if not titre or not contenu:
            flash("Le titre et le contenu sont obligatoires", "error")
            return render_template("community/edit_post.html", filiere=filiere)

        # Créer le post
        post = Post(
            titre=titre,
            contenu=contenu,
            auteur_id=current_user.id,
            filiere_id=filiere_id,
            est_public=True,
        )

        db.session.add(post)
        db.session.flush()  # Pour obtenir l'ID du post

        # Gérer les pièces jointes (Cloudinary Refactor)
        uploaded_files_json = request.form.get("uploaded_files_json")
        if uploaded_files_json:
            try:
                uploaded_files = json.loads(uploaded_files_json)
                for file_data in uploaded_files:
                    # Ajouter la pièce jointe
                    piece_jointe = PieceJointe(
                        nom_fichier=file_data.get("original_name"),
                        chemin_fichier=file_data.get("url"),  # Cloudinary URL
                        type_fichier=file_data.get("type", "document"),
                        type_mime=file_data.get(
                            "format"
                        ),  # Ou deviner depuis l'URL si manquant
                        taille=file_data.get("size"),
                        post_id=post.id,
                    )
                    db.session.add(piece_jointe)
            except json.JSONDecodeError:
                flash("Erreur lors du traitement des pièces jointes", "error")

        db.session.commit()
        flash("Votre publication a été créée avec succès !", "success")

        # Créer une notification pour les abonnés de la filière
        try:
            nb_notifications = NotificationService.notify_new_post(
                post_id=post.id,
                author_name=f"{current_user.prenom} {current_user.nom}",
                post_title=post.titre,
            )
            current_app.logger.info(
                f"Notifications envoyées à {nb_notifications} abonnés de la filière {post.filiere.nom}"
            )
        except Exception as e:
            current_app.logger.error(
                f"Erreur lors de l'envoi des notifications: {str(e)}"
            )

        return redirect(url_for("community.view_post", post_id=post.id))

    return render_template(
        "community/edit_post.html",
        filiere=filiere,
        post=None,
        title="Nouvelle publication",
    )


@community_bp.route("/post/<int:post_id>/modifier", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    """
    Modifie un post existant.

    Cette fonction est appelée lorsqu'un utilisateur souhaite modifier un post existant.
    Elle vérifie les permissions de l'utilisateur et, si les permissions sont correctes,
    met à jour le titre et le contenu du post. Elle supprime également les pièces jointes
    spécifiées dans la requête, puis ajoute les nouvelles pièces jointes si elles sont fournies.

    Paramètres:
        post_id (int): L'ID du post à modifier.

    Retourne:
        Si la requête est une GET, la page HTML correspondante.
        Si la requête est une POST, si la modification du post est effectuée avec succès,
        redirige vers la page de visualisation du post. Sinon, redirige vers la page de modification
        avec un flash d'erreur.

    Exceptions:
        abort(403): Si l'utilisateur n'a pas les permissions nécessaires.
        abort(404): Si le post spécifié n'existe pas.
    """
    from models.post import Post
    from models.piece_jointe import PieceJointe
    from sqlalchemy.orm import joinedload

    post = Post.query.options(joinedload(Post.auteur)).get_or_404(post_id)

    # Vérifier les permissions
    if current_user.id != post.auteur_id and current_user.role not in [
        "admin",
        "enseignant",
    ]:
        abort(403)

    if request.method == "POST":
        post.titre = request.form.get("titre", "").strip()
        post.contenu = request.form.get("contenu", "").strip()
        post.date_modification = datetime.utcnow()

        if not post.titre or not post.contenu:
            flash("Le titre et le contenu sont obligatoires", "error")
            return render_template(
                "community/edit_post.html", post=post, filiere=post.filiere
            )

        # Gérer les pièces jointes (Cloudinary Refactor)
        uploaded_files_json = request.form.get("uploaded_files_json")
        if uploaded_files_json:
            try:
                uploaded_files = json.loads(uploaded_files_json)
                for file_data in uploaded_files:
                    # Ajouter la pièce jointe
                    piece = PieceJointe(
                        nom_fichier=file_data.get("original_name"),
                        chemin_fichier=file_data.get("url"),
                        type_fichier=file_data.get("type", "document"),
                        type_mime=file_data.get("format"),
                        taille=file_data.get("size"),
                        post_id=post.id,
                    )
                    db.session.add(piece)
            except json.JSONDecodeError:
                flash("Erreur lors du traitement des nouvelles pièces jointes", "error")

        db.session.commit()
        flash("Publication mise à jour avec succès!", "success")

        # Créer une notification pour les abonnés de la filière (sauf l'auteur)
        try:
            nb_notifications = NotificationService.notify_post_update(
                post_id=post.id,
                author_name=f"{current_user.prenom} {current_user.nom}",
                post_title=post.titre,
            )
            if nb_notifications > 0:
                current_app.logger.info(
                    f"Notifications de mise à jour envoyées à {nb_notifications} abonnés de la filière {post.filiere.nom}"
                )
        except Exception as e:
            current_app.logger.error(
                f"Erreur lors de l'envoi des notifications de mise à jour: {str(e)}"
            )

        return redirect(url_for("community.view_post", post_id=post.id))

    return render_template("community/edit_post.html", post=post, filiere=post.filiere)


@community_bp.route("/post/<int:post_id>/supprimer", methods=["POST"])
@login_required
def delete_post(post_id):
    """
    Supprime un post.

    Cette fonction est appelée lorsque l'utilisateur souhaite supprimer un post.
    Elle vérifie les permissions de l'utilisateur avant de supprimer le post de la base de données.

    Paramètres:
        - post_id: L'ID du post à supprimer.

    Retourne:
        - Redirige vers la page d'accueil si l'utilisateur n'a pas les permissions nécessaires.
        - Redirige vers la page d'accueil si le post n'existe pas.
        - Redirige vers la page d'accueil si tout est correct.

    Exceptions:
        - None
    """
    from models.post import Post
    from sqlalchemy.orm import joinedload

    post = Post.query.options(joinedload(Post.auteur)).get_or_404(post_id)
    filiere_id = post.filiere_id

    # Vérifier les permissions
    if current_user.id != post.auteur_id and current_user.role not in [
        "admin",
        "enseignant",
    ]:
        abort(403)

    # Supprimer les pièces jointes physiques
    for piece in post.pieces_jointes:
        try:
            filepath = os.path.join(
                current_app.config["UPLOAD_FOLDER"], piece.chemin_fichier
            )
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            current_app.logger.error(
                f"Erreur lors de la suppression du fichier {piece.chemin_fichier}: {e}"
            )

    # Supprimer le post (les dépendances en cascade devraient s'occuper du reste)
    db.session.delete(post)
    db.session.commit()

    flash("Publication supprimée avec succès!", "success")
    return redirect(url_for("community.filiale", filiere_id=filiere_id))


@community_bp.route("/post/<int:post_id>/commenter", methods=["POST"])
@login_required
def add_comment(post_id):
    """
    Ajoute un commentaire à un post.

    Cette fonction est appelée lorsque l'utilisateur souhaite ajouter un commentaire à un post.
    Elle crée un nouveau commentaire avec le contenu fourni par l'utilisateur et l'associe au post spécifié.

    Paramètres:
        - post_id: L'ID du post auquel ajouter le commentaire.

    Retourne:
        - Redirige vers la page du post si tout est correct.

    Exceptions:
        - None
    """
    from models.post import Post
    from models.commentaire import Commentaire
    from sqlalchemy.orm import joinedload

    post = Post.query.options(joinedload(Post.auteur)).get_or_404(post_id)

    # Vérifier les permissions
    if (
        current_user.role == "etudiant"
        and post.filiere.nom != current_user.etudiant.filiere
    ):
        abort(403)

    contenu = request.form.get("contenu", "").strip()

    if not contenu:
        flash("Le commentaire ne peut pas être vide", "error")
        return redirect(url_for("community.view_post", post_id=post_id))

    # Vérifier que l'utilisateur actuel existe bien dans la base de données
    from models.user import User

    user_exists = User.query.get(current_user.id)
    if not user_exists:
        # Forcer la déconnexion si l'utilisateur n'existe plus
        from flask_login import logout_user

        logout_user()
        flash("Votre session a expiré. Veuillez vous reconnecter.", "error")
        return redirect(url_for("auth.login"))

    # Créer le commentaire
    commentaire = Commentaire(
        contenu=contenu, auteur_id=current_user.id, post_id=post_id
    )

    db.session.add(commentaire)

    # Créer une notification pour l'auteur du post en utilisant le service
    try:
        notification_sent = NotificationService.notify_post_author(
            post_id=post_id,
            commenter_id=current_user.id,
            commenter_name=f"{current_user.prenom} {current_user.nom}",
            post_title=post.titre,
        )
        if notification_sent:
            current_app.logger.info(
                f"Notification envoyée à l'auteur du post {post_id}"
            )
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")

    db.session.commit()

    flash("Commentaire ajouté!", "success")
    return redirect(
        url_for("community.view_post", post_id=post_id)
        + "#comment-"
        + str(commentaire.id)
    )


@community_bp.route("/comment/<int:comment_id>/supprimer", methods=["POST"])
@login_required
def delete_comment(comment_id):
    """
    Supprime un commentaire.

    Cette fonction est appelée lorsque l'utilisateur souhaite supprimer un commentaire.
    Elle vérifie que l'utilisateur est l'auteur du commentaire ou un administrateur
    avant de supprimer le commentaire de la base de données.

    Args:
        comment_id (int): Identifiant unique du commentaire à supprimer.

    Returns:
        None
    """
    from models.commentaire import Commentaire

    commentaire = Commentaire.query.get_or_404(comment_id)
    post = commentaire.post

    # Vérifier que l'utilisateur est l'auteur du commentaire ou un administrateur
    if current_user.id != commentaire.auteur_id and current_user.role not in [
        "admin",
        "enseignant",
    ]:
        abort(403)

    db.session.delete(commentaire)
    db.session.commit()

    flash("Commentaire supprimé avec succès.", "success")
    return redirect(url_for("community.view_post", post_id=post.id))


@community_bp.route("/post/<int:post_id>/epingler", methods=["POST"])
@login_required
@filiere_admin_required
def toggle_pin(post_id):
    """
    Épingler ou désépingler un post (seulement accessible par les administrateurs).

    Cette fonction est appelée lorsque l'utilisateur souhaite épingler ou désépingler un post.
    Elle vérifie que l'utilisateur est un administrateur avant d'épingler ou de désépingler le post.

    Args:
        post_id (int): Identifiant unique du post à épingler ou à désépingler.

    Returns:
        None
    """
    from models.post import Post
    from sqlalchemy.orm import joinedload

    post = Post.query.options(joinedload(Post.auteur)).get_or_404(post_id)
    post.est_epingle = not post.est_epingle
    db.session.commit()

    action = "épinglée" if post.est_epingle else "désépinglée"
    flash(f"Publication {action} avec succès!", "success")

    return redirect(request.referrer or url_for("community.view_post", post_id=post_id))


@community_bp.route("/fichier/<int:attachment_id>")
@login_required
def download_attachment(attachment_id):
    """
    Télécharger une pièce jointe.

    Cette fonction est appelée lorsque l'utilisateur souhaite télécharger une pièce jointe.
    Elle récupère la pièce jointe correspondante à l'identifiant fourni et la télécharge
    au format défini dans les paramètres de configuration.

    Args:
        attachment_id (int): Identifiant unique de la pièce jointe à télécharger.

    Returns:
        Flask Response: Une réponse contenant le fichier téléchargé.

    Raises:
        werkzeug.exceptions.NotFound: Si la pièce jointe n'est pas trouvée.
    """
    from models.piece_jointe import PieceJointe

    piece = PieceJointe.query.get_or_404(attachment_id)
    post = piece.post

    # Vérifier les permissions
    if (
        current_user.role == "etudiant"
        and post.filiere.nom != current_user.etudiant.filiere
    ):
        return (
            render_template(
                "error.html",
                title="Accès non autorisé",
                message="Vous n'avez pas accès à cette page.",
            ),
            403,
        )

    # Vérifier que le fichier existe
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], piece.chemin_fichier)
    if not os.path.exists(filepath):
        flash("Le fichier demandé n'existe plus.", "error")
        return redirect(url_for("community.view_post", post_id=post.id))

    # Incrémenter le compteur de téléchargements si nécessaire
    piece.downloads += 1
    db.session.commit()

    # Envoyer le fichier
    return send_from_directory(
        os.path.dirname(filepath),
        os.path.basename(filepath),
        as_attachment=True,
        download_name=piece.nom_fichier,
    )


@community_bp.route("/admin/filieres")
@login_required
def manage_admins():
    """
    Gère les administrateurs des filières.

    Cette fonction permet aux administrateurs principaux de gérer les administrateurs
    des filières. Elle est accessible uniquement aux administrateurs principaux.

    Args:
        None

    Returns:
        None

    Raises:
        werkzeug.exceptions.Forbidden: Si l'utilisateur n'est pas un administrateur principal.
    """
    if current_user.role != "admin":
        return (
            render_template(
                "error.html",
                title="Accès non autorisé",
                message="Vous n'avez pas accès à cette page.",
            ),
            403,
        )

    # Imports locaux pour éviter les imports circulaires
    from models.filiere import Filiere, FiliereAdmin
    from models.enseignant import Enseignant
    from models.user import User

    # Récupérer toutes les filières avec leurs administrateurs
    filieres = Filiere.query.options(
        db.joinedload(Filiere.admins)
        .joinedload(FiliereAdmin.enseignant)
        .joinedload(Enseignant.user)
    ).all()

    # Récupérer tous les enseignants pour le formulaire d'ajout
    enseignants = (
        Enseignant.query.join(User, Enseignant.user_id == User.id)
        .order_by(User.nom, User.prenom)
        .all()
    )

    return render_template(
        "community/manage_admins.html", filieres=filieres, enseignants=enseignants
    )


@community_bp.route("/admin/filiere/<int:filiere_id>/ajouter-admin", methods=["POST"])
@login_required
def add_filiere_admin(filiere_id):
    """
    Ajoute un administrateur à une filière.

    Cette fonction permet aux administrateurs principaux de gérer les
    administrateurs de chaque filière. Elle permet d'ajouter un nouvel
    administrateur à une filière spécifique.

    Args:
        filiere_id (int): Identifiant de la filière à laquelle ajouter un
            administrateur.

    Returns:
        None

    Raises:
        werkzeug.exceptions.Forbidden: Si l'utilisateur n'est pas un
            administrateur principal.
    """
    if current_user.role != "admin":
        return (
            render_template(
                "error.html",
                title="Accès non autorisé",
                message="Vous n'avez pas accès à cette page.",
            ),
            403,
        )

    # Imports locaux pour éviter les imports circulaires
    from models.filiere import FiliereAdmin

    enseignant_id = request.form.get("enseignant_id", type=int)

    if not enseignant_id:
        flash("Veuillez sélectionner un enseignant", "error")
        return redirect(url_for("community.manage_admins"))

    # Vérifier si l'enseignant est déjà admin de cette filière
    existing = FiliereAdmin.query.filter_by(
        filiere_id=filiere_id, enseignant_id=enseignant_id
    ).first()

    if existing:
        flash("Cet enseignant est déjà administrateur de cette filière", "warning")
        return redirect(url_for("community.manage_admins"))

    # Ajouter l'administrateur
    admin = FiliereAdmin(filiere_id=filiere_id, enseignant_id=enseignant_id)

    db.session.add(admin)
    db.session.commit()

    flash("Administrateur ajouté avec succès!", "success")
    return redirect(url_for("community.manage_admins"))


@community_bp.route(
    "/admin/filiere/<int:filiere_id>/retirer-admin/<int:enseignant_id>",
    methods=["POST"],
)
@login_required
def remove_filiere_admin(filiere_id, enseignant_id):
    """
    Retire un administrateur d'une filière (seulement pour les administrateurs principaux).

    Cette fonction est accessible uniquement aux administrateurs principaux.

    Paramètres:
        filiere_id (int): Identifiant de la filière.
        enseignant_id (int): Identifiant de l'enseignant à retirer.

    Retourne:
        None

    Levée:
        werkzeug.exceptions.Forbidden: Si l'utilisateur n'est pas un
            administrateur principal.
    """
    if current_user.role != "admin":
        return (
            render_template(
                "error.html",
                title="Accès non autorisé",
                message="Vous n'avez pas accès à cette page.",
            ),
            403,
        )

    # Imports locaux pour éviter les imports circulaires
    from models.filiere import FiliereAdmin

    admin = FiliereAdmin.query.filter_by(
        filiere_id=filiere_id, enseignant_id=enseignant_id
    ).first_or_404()

    db.session.delete(admin)
    db.session.commit()

    flash("Administrateur retiré avec succès!", "success")
    return redirect(url_for("community.manage_admins"))


# Fonction utilitaire pour créer le dossier de téléchargement s'il n'existe pas
def init_upload_folder():
    """S'assure que le dossier de téléchargement existe"""
    upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "community")
    os.makedirs(upload_folder, exist_ok=True)


# Fonction d'initialisation appelée lors de l'enregistrement du blueprint
def init_community_upload_folder(app):
    """Initialise le dossier de téléchargement pour la communauté"""
    with app.app_context():
        upload_folder = os.path.join(app.config["UPLOAD_FOLDER"], "community")
        os.makedirs(upload_folder, exist_ok=True)
