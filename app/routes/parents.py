from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.models.etudiant import Etudiant
from app.models.parent import Parent
from app.models.note import Note
from app.models.presence import Presence
from app.models.notification import Notification

parents_bp = Blueprint("parents", __name__, url_prefix="/parent")


@parents_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "parent":
        flash("Accès réservé aux parents.", "error")
        return redirect(url_for("main.index"))

    # Récupérer les enfants liés
    parents_records = Parent.query.filter_by(user_id=current_user.id).all()
    children = []

    total_avg = 0
    count_avg = 0
    total_presence = 0
    count_presence = 0

    for p in parents_records:
        etudiant = p.etudiant
        # Calcul stats individuelles pour enrichir l'objet etudiant temporairement
        notes = Note.query.filter_by(etudiant_id=etudiant.id).all()
        etudiant.average = None
        if notes:
            etudiant.average = round(
                sum(n.note for n in notes if n.note is not None) / len(notes), 2
            )
            total_avg += etudiant.average
            count_avg += 1

        total_c = Presence.query.filter_by(etudiant_id=etudiant.id).count()
        total_p = Presence.query.filter_by(
            etudiant_id=etudiant.id, present=True
        ).count()
        etudiant.presence_rate = (
            round((total_p / total_c) * 100, 1) if total_c > 0 else 0.0
        )

        total_presence += etudiant.presence_rate
        count_presence += 1

        etudiant.unread_notifs = Notification.query.filter_by(
            user_id=current_user.id, est_lue=False
        ).count()
        children.append(etudiant)

    global_average = round(total_avg / count_avg, 2) if count_avg > 0 else "--"
    global_presence = (
        round(total_presence / count_presence, 1) if count_presence > 0 else "--"
    )

    return render_template(
        "parents/dashboard.html",
        children=children,
        global_average=global_average,
        global_presence=global_presence,
    )


@parents_bp.route("/link-child", methods=["POST"])
@login_required
def link_child():
    if current_user.role != "parent":
        return jsonify({"success": False, "message": "Accès non autorisé"}), 403

    code = request.form.get("code")
    if not code:
        return jsonify({"success": False, "message": "Code requis"}), 400

    etudiant = Etudiant.query.filter_by(code_parent=code).first()
    if not etudiant:
        return (
            jsonify(
                {"success": False, "message": "Code invalide ou étudiant introuvable"}
            ),
            404,
        )

    # Vérifier si déjà lié
    existing_link = Parent.query.filter_by(
        user_id=current_user.id, etudiant_id=etudiant.id
    ).first()
    if existing_link:
        return (
            jsonify(
                {"success": False, "message": "Cet enfant est déjà lié à votre compte"}
            ),
            400,
        )

    from app.extensions import db

    new_link = Parent(user_id=current_user.id, etudiant_id=etudiant.id)
    db.session.add(new_link)

    # Optionnel: marquer le code comme utilisé ou le supprimer si on veut qu'il soit unique à un seul parent
    # Mais généralement un code peut être utilisé par les deux parents.

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f"Félicitations ! Vous êtes maintenant lié à {etudiant.user.prenom} {etudiant.user.nom}",
        }
    )


@parents_bp.route("/enfant/<int:etudiant_id>")
@login_required
def view_child(etudiant_id):
    if current_user.role != "parent":
        flash("Accès réservé aux parents.", "error")
        return redirect(url_for("main.index"))

    # Vérifier l'autorisation
    parent_record = Parent.query.filter_by(
        user_id=current_user.id, etudiant_id=etudiant_id
    ).first()
    if not parent_record:
        flash("Vous n'êtes pas autorisé à voir cet étudiant.", "error")
        return redirect(url_for("parents.dashboard"))

    etudiant = Etudiant.query.get_or_404(etudiant_id)

    # Stats rapides
    notes = Note.query.filter_by(etudiant_id=etudiant.id).all()
    if notes:
        average = round(
            sum(n.note for n in notes if n.note is not None) / len(notes), 2
        )
    else:
        average = None

    total_cours = Presence.query.filter_by(etudiant_id=etudiant.id).count()
    total_present = Presence.query.filter_by(
        etudiant_id=etudiant.id, present=True
    ).count()
    presence = round((total_present / total_cours) * 100, 1) if total_cours > 0 else 0.0

    # Dernières notes
    recent_grades = (
        Note.query.filter_by(etudiant_id=etudiant.id)
        .order_by(Note.date_evaluation.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "parents/child_detail.html",
        etudiant=etudiant,
        average=average,
        presence=presence,
        recent_grades=recent_grades,
    )


@parents_bp.route("/notifications")
@login_required
def parent_notifications():
    if current_user.role != "parent":
        flash("Accès réservé aux parents.", "error")
        return redirect(url_for("main.index"))

    # Récupérer les notifications pour le parent
    user_notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.date_creation.desc())
        .all()
    )

    # Marquer comme lues
    for n in user_notifications:
        if not n.est_lue:
            n.est_lue = True
    from app.extensions import db

    db.session.commit()

    return render_template(
        "parents/notifications.html", notifications=user_notifications
    )


@parents_bp.route("/enfant/<int:etudiant_id>/calendrier")
@login_required
def view_calendar(etudiant_id):
    if current_user.role != "parent":
        flash("Accès réservé aux parents.", "error")
        return redirect(url_for("main.index"))

    parent_record = Parent.query.filter_by(
        user_id=current_user.id, etudiant_id=etudiant_id
    ).first()
    if not parent_record:
        flash("Accès non autorisé.", "error")
        return redirect(url_for("parents.dashboard"))

    etudiant = Etudiant.query.get_or_404(etudiant_id)
    return render_template("parents/calendar.html", etudiant=etudiant)


@parents_bp.route("/api/enfant/<int:etudiant_id>/events")
@login_required
def get_calendar_events(etudiant_id):
    if current_user.role != "parent":
        return jsonify({"error": "Unauthorized"}), 403

    parent_record = Parent.query.filter_by(
        user_id=current_user.id, etudiant_id=etudiant_id
    ).first()
    if not parent_record:
        return jsonify({"error": "Unauthorized"}), 403

    # Récupérer les absences
    absences = Presence.query.filter_by(etudiant_id=etudiant_id, present=False).all()
    events = []
    for abs in absences:
        events.append(
            {
                "title": f"Absence : {abs.matiere.nom}",
                "start": abs.date_presence.isoformat(),
                "color": "#ef4444",  # Red
                "allDay": True,
                "type": "absence",
            }
        )

    # Récupérer les notes (comme événements de évaluation)
    notes = Note.query.filter_by(etudiant_id=etudiant_id).all()
    for n in notes:
        events.append(
            {
                "title": f"Note : {n.matiere.nom} ({n.note}/20)",
                "start": n.date_evaluation.isoformat(),
                "color": "#3b82f6",  # Blue
                "allDay": True,
                "type": "grade",
                "description": f"Évaluation : {n.type_evaluation}",
            }
        )

    return jsonify(events)
