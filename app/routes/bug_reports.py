from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.models.bug_report import BugReport
from app.forms import BugReportForm, BugReportAdminForm
from app.extensions import db
from datetime import datetime

# Configuration du répertoire de stockage des captures d'écran
UPLOAD_FOLDER = os.path.join("uploads", "bug_reports")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# Création du Blueprint
bug_reports = Blueprint("bug_reports", __name__)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bug_reports.route("/bug-reports", methods=["GET"])
@login_required
def list_bug_reports():
    """
    Affiche la liste des rapports de bugs.

    Cette fonction est l'endpoint de la route '/bug-reports'. Elle est accessible uniquement
    aux utilisateurs authentifiés. Elle permet de récupérer la page numéro `page` des rapports
    de bugs triés par statut, priorité et date de création. Si aucun numéro de page n'est fourni,
    la page par défaut est la première.

    Paramètres:
        - page (int): Numéro de page des rapports de bugs à afficher. Par défaut, la première page.

    Retourne:
        Une réponse HTML contenant la liste des rapports de bugs triés par statut, priorité et date de création.
    """
    page = request.args.get("page", 1, type=int)
    per_page = 10

    # Pour les administrateurs, afficher tous les rapports
    if current_user.role == "admin":
        bug_reports = BugReport.query.order_by(
            BugReport.status.asc(),
            BugReport.priority.desc(),
            BugReport.created_at.desc(),
        ).paginate(page=page, per_page=per_page, error_out=False)
    else:
        # Pour les utilisateurs normaux, n'afficher que leurs rapports
        bug_reports = (
            BugReport.query.filter_by(user_id=current_user.id)
            .order_by(
                BugReport.status.asc(),
                BugReport.priority.desc(),
                BugReport.created_at.desc(),
            )
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    return render_template("bug_reports/list.html", bug_reports=bug_reports)


@bug_reports.route("/bug-reports/new", methods=["GET", "POST"])
@login_required
def new_bug_report():
    """
    Crée un nouveau rapport de bug.

    Cette fonction est l'endpoint de la route '/bug-reports/new'. Elle est accessible
    uniquement aux utilisateurs authentifiés. Elle permet de créer un nouveau rapport
    de bug en utilisant le formulaire BugReportForm. Le formulaire est validé et si les
    données sont valides, un nouveau rapport de bug est créé avec les informations fournies
    par l'utilisateur. Un message flash est ensuite affiché indiquant que le rapport a été
    créé avec succès.

    Paramètres:
        Aucun

    Retourne:
        Si la création du rapport de bug échoue, une réponse HTML contenant le formulaire
        BugReportForm et un message d'erreur. Si la création du rapport de bug réussit,
        une redirection vers la page d'accueil est effectuée.
    """
    form = BugReportForm()

    if form.validate_on_submit():
        # Créer un nouveau rapport de bug
        bug_report = BugReport(
            title=form.title.data,
            description=form.description.data,
            steps_to_reproduce=form.steps_to_reproduce.data,
            priority=form.priority.data,
            user_id=current_user.id,
        )

        # Remplacer la partie de code qui gère le téléchargement de l'image par :
        if "screenshot" in request.files:
            file = request.files["screenshot"]
            if file and file.filename != "" and allowed_file(file.filename):
                # Créer le répertoire s'il n'existe pas
                upload_dir = os.path.join(current_app.static_folder, UPLOAD_FOLDER)
                os.makedirs(upload_dir, exist_ok=True)

                # Générer un nom de fichier sécurisé
                filename = f"bug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # Stocker uniquement le chemin relatif
                bug_report.image_path = os.path.join(UPLOAD_FOLDER, filename).replace(
                    "\\", "/"
                )
        db.session.add(bug_report)
        db.session.commit()

        flash(
            "Votre rapport de bug a été soumis avec succès. Merci pour votre contribution !",
            "success",
        )
        return redirect(url_for("bug_reports.list_bug_reports"))

    return render_template("bug_reports/new.html", form=form)


@bug_reports.route("/bug-reports/<int:report_id>", methods=["GET"])
@login_required
def view_bug_report(report_id):
    """
    Affiche les détails d'un rapport de bug.

    Cette fonction récupère le rapport de bug associé à l'identifiant donné
    à partir de la base de données. Si le rapport de bug n'est pas trouvé, une
    erreur 404 est retournée.

    Paramètres:
        report_id (int): Identifiant unique du rapport de bug à afficher.

    Retourne:
        Une réponse HTML contenant les détails du rapport de bug.

    Levée:
        FlaskHTTPException: Si le rapport de bug n'est pas trouvé.
    """
    bug_report = BugReport.query.get_or_404(report_id)

    # Vérifier que l'utilisateur a le droit de voir ce rapport
    if current_user.role != "admin" and bug_report.user_id != current_user.id:
        flash("Vous n'êtes pas autorisé à accéder à cette page.", "error")
        return redirect(url_for("bug_reports.list_bug_reports"))

    # Formulaire d'administration (uniquement pour les admins)
    admin_form = None
    if current_user.role == "admin":
        admin_form = BugReportAdminForm()
        admin_form.status.data = bug_report.status

    return render_template(
        "bug_reports/view.html", bug_report=bug_report, admin_form=admin_form
    )


@bug_reports.route("/bug-reports/<int:report_id>/update", methods=["POST"])
@login_required
def update_bug_report(report_id):
    """
    Met à jour un rapport de bug.

    Cette fonction est accessible uniquement aux administrateurs. Elle permet de
    mettre à jour les informations d'un rapport de bug existant. Les informations
    mises à jour comprennent le statut, les notes d'administration et la date de
    mise à jour.

    Paramètres:
        report_id (int): Identifiant unique du rapport de bug à mettre à jour.

    Retourne:
        Une redirection vers la page des détails du rapport de bug mis à jour.

    Levée:
        None
    """
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("bug_reports.list_bug_reports"))

    bug_report = BugReport.query.get_or_404(report_id)
    form = BugReportAdminForm()

    if form.validate_on_submit():
        bug_report.status = form.status.data
        if form.admin_notes.data:
            bug_report.admin_notes = form.admin_notes.data
        bug_report.updated_at = datetime.utcnow()

        db.session.commit()
        flash("Le rapport a été mis à jour avec succès.", "success")

    return redirect(url_for("bug_reports.view_bug_report", report_id=bug_report.id))


@bug_reports.route("/bug-reports/<int:report_id>/edit", methods=["GET", "POST"])
@login_required
def edit_bug_report(report_id):
    """
    Modifie un rapport de bug existant.

    Cette fonction est accessible uniquement aux utilisateurs authentifiés. Elle permet
    de mettre à jour les informations d'un rapport de bug existant. Les informations
    mises à jour peuvent varier en fonction du rôle de l'utilisateur. Les utilisateurs
    normaux peuvent modifier le titre, la description, les étapes pour le reproduire,
    la priorité et l'image de capture d'écran. Les administrateurs peuvent également mettre à
    jour le statut, les notes d'administration et la date de mise à jour.

    Paramètres:
        report_id (int): Identifiant unique du rapport de bug à mettre à jour.

    Retourne:
        Si la modification du rapport de bug échoue, une réponse HTML contenant le formulaire
        approprié et un message d'erreur. Si la modification du rapport de bug réussit, une
        redirection vers la page des détails du rapport de bug mis à jour est effectuée.

    Levée:
        None
    """
    bug_report = BugReport.query.get_or_404(report_id)

    # Vérifier que l'utilisateur a le droit de modifier ce rapport
    if current_user.role != "admin" and bug_report.user_id != current_user.id:
        flash("Vous n'êtes pas autorisé à modifier ce rapport.", "error")
        return redirect(url_for("bug_reports.list_bug_reports"))

    # Utiliser BugReportForm pour les utilisateurs normaux, BugReportAdminForm pour les admins
    form = (
        BugReportAdminForm()
        if current_user.role == "admin"
        else BugReportForm(obj=bug_report)
    )

    if form.validate_on_submit():
        bug_report.title = form.title.data
        bug_report.description = form.description.data
        bug_report.steps_to_reproduce = form.steps_to_reproduce.data
        bug_report.priority = form.priority.data
        bug_report.updated_at = datetime.utcnow()

        # Mettre à jour le statut uniquement si l'utilisateur est admin
        if current_user.role == "admin":
            bug_report.status = form.status.data
            bug_report.admin_notes = form.admin_notes.data

        # Gérer la suppression de l'image existante
        if request.form.get("remove_image") == "y":
            if bug_report.image_path:
                try:
                    file_path = os.path.join(
                        current_app.static_folder, bug_report.image_path
                    )
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
                bug_report.image_path = None

        # Gérer le téléchargement d'une nouvelle image
        if "screenshot" in request.files:
            file = request.files["screenshot"]
            if file and file.filename != "" and allowed_file(file.filename):
                # Supprimer l'ancienne image si elle existe
                if bug_report.image_path:
                    try:
                        old_file = os.path.join(
                            current_app.static_folder, bug_report.image_path
                        )
                        if os.path.exists(old_file):
                            os.remove(old_file)
                    except Exception:
                        pass

                # Créer le répertoire s'il n'existe pas
                upload_dir = os.path.join(current_app.static_folder, UPLOAD_FOLDER)
                os.makedirs(upload_dir, exist_ok=True)

                # Générer un nom de fichier sécurisé
                filename = f"bug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                bug_report.image_path = os.path.join(UPLOAD_FOLDER, filename).replace(
                    "\\", "/"
                )

        db.session.commit()
        flash("Le rapport a été mis à jour avec succès.", "success")
        return redirect(url_for("bug_reports.view_bug_report", report_id=bug_report.id))

    # Pré-remplir le formulaire avec les données existantes
    if request.method == "GET":
        form.title.data = bug_report.title
        form.description.data = bug_report.description
        form.steps_to_reproduce.data = bug_report.steps_to_reproduce
        form.priority.data = bug_report.priority
        if current_user.role == "admin":
            form.status.data = bug_report.status
            form.admin_notes.data = bug_report.admin_notes

    return render_template("bug_reports/edit.html", bug_report=bug_report, form=form)


@bug_reports.route("/bug-reports/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_bug_report(report_id):
    """
    Supprime un rapport de bug.

    Cette fonction est accessible uniquement aux utilisateurs authentifiés. Elle
    permet de supprimer un rapport de bug existant de la base de données.

    Paramètres:
        report_id (int): Identifiant unique du rapport de bug à supprimer.

    Retourne:
        Une redirection vers la page des rapports de bug.

    Levée:
        None
    """
    bug_report = BugReport.query.get_or_404(report_id)

    # Vérifier que l'utilisateur a le droit de supprimer ce rapport
    if current_user.role != "admin" and bug_report.user_id != current_user.id:
        flash("Vous n'êtes pas autorisé à supprimer ce rapport.", "error")
        return redirect(url_for("bug_reports.list_bug_reports"))

    # Remplacer la suppression de l'image par :
    if bug_report.image_path:
        try:
            file_path = os.path.join(current_app.static_folder, bug_report.image_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
    # Supprimer le rapport de la base de données
    db.session.delete(bug_report)
    db.session.commit()

    flash("Le rapport a été supprimé avec succès.", "success")
    return redirect(url_for("bug_reports.list_bug_reports"))
