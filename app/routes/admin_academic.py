from flask import Blueprint, render_template, flash, request, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.etudiant import Etudiant
from app.models.academic import (
    AcademicArchivedStudent,
    AcademicArchivedGrade,
    PromotionRule,
)
from app.models.academic_year_config import AcademicYearConfig
from app.models.evaluation_period import EvaluationPeriod
from app.services.academic_engine import AcademicEngine

admin_academic_bp = Blueprint("admin_academic", __name__, url_prefix="/admin/academic")


@admin_academic_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Tableau de bord de gestion académique.
    Affiche la liste des étudiants éligibles à la clôture.
    """
    if current_user.role != "admin":
        flash("Accès réservé aux administrateurs.", "error")
        return redirect(url_for("main.index"))

    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = Etudiant.query.paginate(page=page, per_page=per_page, error_out=False)
    students = pagination.items

    progression_data = []

    for s in students:
        result = AcademicEngine.evaluate_student_progression(s.id)
        if result:
            progression_data.append(result)

    return render_template(
        "admin/academic/dashboard.html",
        students_data=progression_data,
        pagination=pagination,
    )


def process_annual_closing(app, admin_id):
    """
    Tâche de fond pour le traitement de la clôture annuelle.
    """
    with app.app_context():
        try:
            students = Etudiant.query.all()
            count_admis = 0
            count_redouble = 0

            PROMOTION_MAP = {
                "Licence 1": "Licence 2",
                "Licence 2": "Licence 3",
                "Licence 3": "Master 1",
                "Master 1": "Master 2",
                "Master 2": "Diplômé",
            }

            for s in students:
                result = AcademicEngine.evaluate_student_progression(s.id)
                if not result:
                    continue

                archive = AcademicArchivedStudent(
                    student_user_id=s.user_id,
                    annee_academique=s.annee,
                    filiere_nom=s.filiere,
                    niveau=s.annee,
                    moyenne_generale=result["moyenne_generale"],
                    credits_total_valides=result["credits_total"],
                    decision_jury=result["decision"],
                    archived_by_id=admin_id,
                )
                db.session.add(archive)
                db.session.flush()

                for detail in result["details"]:
                    matiere = detail["matiere"]
                    stats = detail["stats"]
                    archived_grade = AcademicArchivedGrade(
                        archive_id=archive.id,
                        matiere_nom=matiere.nom,
                        code_matiere=matiere.code,
                        credits_matiere=matiere.credit,
                        moyenne_matiere=stats["moyenne"],
                        note_examen=stats["note_exam"],
                        note_classe=stats["note_cc"],
                        semestre=matiere.semestre,
                        is_validated=stats["is_validated"],
                        statut="VALIDÉE" if stats["is_validated"] else "A RATTRAPER",
                    )
                    db.session.add(archived_grade)

                if result["decision"] == "ADMIS":
                    count_admis += 1
                    current_level = s.annee
                    next_level = PROMOTION_MAP.get(current_level)
                    if next_level:
                        s.annee = next_level
                else:
                    count_redouble += 1

            db.session.commit()
            print(
                f"Clôture terminée : {count_admis} admis, {count_redouble} redoublements."
            )
            # TODO: Envoyer une notification système à l'admin

        except Exception as e:
            db.session.rollback()
            print(f"Erreur background clôture : {str(e)}")


@admin_academic_bp.route("/cloturer-annee", methods=["POST"])
@login_required
def cloturer_annee():
    """
    Action critique : Lance l'archivage en tâche de fond.
    """
    if current_user.role != "admin":
        return redirect(url_for("main.index"))

    import threading
    from flask import current_app

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=process_annual_closing, args=(app, current_user.id)
    )
    thread.start()

    flash(
        "La clôture annuelle a démarré en tâche de fond. Cela peut prendre quelques minutes.",
        "info",
    )
    return redirect(url_for("admin_academic.dashboard"))


@admin_academic_bp.route("/download/<int:student_id>")
@login_required
def download_transcript(student_id):
    """
    Génère et télécharge le relevé de notes (Provisoire ou Officiel via student_id).
    """
    if current_user.role not in ["admin", "etudiant", "enseignant"]:
        return redirect(url_for("main.index"))

    from app.services.document_service import DocumentService
    from flask import make_response

    pdf = DocumentService.generate_transcript_pdf(student_id=student_id)

    if not pdf:
        flash("Impossible de générer le relevé.", "error")
        return redirect(request.referrer or url_for("main.index"))

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=releve_{student_id}.pdf"
    )
    return response


@admin_academic_bp.route("/download/archive/<int:archive_id>")
@login_required
def download_archive(archive_id):
    """
    Télécharge le relevé de notes depuis une archive spécifique.
    """
    if current_user.role not in ["admin", "enseignant", "etudiant"]:
        return redirect(url_for("main.index"))

    from app.services.document_service import DocumentService
    from flask import make_response

    pdf = DocumentService.generate_transcript_pdf(archive_id=archive_id)

    if not pdf:
        flash("Erreur lors de la génération du PDF.", "error")
        return redirect(request.referrer or url_for("main.index"))

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=releve_archive_{archive_id}.pdf"
    )
    return response


@admin_academic_bp.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar_view():
    """
    Gestion du calendrier académique et des périodes d'évaluation.
    """
    if current_user.role != "admin":
        return redirect(url_for("main.index"))

    config = AcademicYearConfig.query.filter_by(is_active=True).first()
    periods = EvaluationPeriod.query.order_by(EvaluationPeriod.start_date.desc()).all()

    if request.method == "POST":
        # Mise à jour de la configuration globale
        current_year = request.form.get("current_year")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        semester_split = request.form.get("semester_split_date")

        from datetime import datetime

        if not config:
            config = AcademicYearConfig(is_active=True)
            db.session.add(config)

        config.current_year = current_year
        config.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        config.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        if semester_split:
            config.semester_split_date = datetime.strptime(
                semester_split, "%Y-%m-%d"
            ).date()

        db.session.commit()
        flash("Configuration du calendrier mise à jour.", "success")
        return redirect(url_for("admin_academic.calendar_view"))

    return render_template(
        "admin/academic/calendar.html", config=config, periods=periods
    )


@admin_academic_bp.route("/calendar/period/add", methods=["POST"])
@login_required
def add_period():
    if current_user.role != "admin":
        return redirect(url_for("main.index"))

    from datetime import datetime

    name = request.form.get("name")
    type_eval = request.form.get("type_eval")
    start = request.form.get("start_date")
    end = request.form.get("end_date")

    new_period = EvaluationPeriod(
        name=name,
        type_eval=type_eval,
        start_date=datetime.strptime(start, "%Y-%m-%d").date(),
        end_date=datetime.strptime(end, "%Y-%m-%d").date(),
    )
    db.session.add(new_period)
    db.session.commit()
    flash("Période d'évaluation ajoutée.", "success")
    return redirect(url_for("admin_academic.calendar_view"))


@admin_academic_bp.route("/calendar/period/delete/<int:id>", methods=["POST"])
@login_required
def delete_period(id):
    if current_user.role != "admin":
        return redirect(url_for("main.index"))

    period = EvaluationPeriod.query.get_or_404(id)
    db.session.delete(period)
    db.session.commit()
    flash("Période supprimée.", "success")
    return redirect(url_for("admin_academic.calendar_view"))
