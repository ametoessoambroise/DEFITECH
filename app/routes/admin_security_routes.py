"""
Routes administrateur pour la gestion des incidents de sécurité
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.extensions import db
from app.models.security_incident import SecurityIncident
from app.models.user import User
from app.models.etudiant import Etudiant


# Ces routes sont à ajouter dans admin.py


# Route 1: Liste des incidents de sécurité
def admin_security_incidents():
    """Liste tous les incidents de sécurité détectés par l'IA"""
    if current_user.role != "admin":
        flash("Accès non autorisé.", "error")
        return redirect(url_for("main.index"))

    # Filtres
    status_filter = request.args.get("status", "all")  # all, unresolved, resolved

    # Query de base
    query = SecurityIncident.query

    # Appliquer les filtres
    if status_filter == "unresolved":
        query = query.filter_by(is_resolved=False)
    elif status_filter == "resolved":
        query = query.filter_by(is_resolved=True)

    # Trier par date desc (plus récents en premier)
    incidents = query.order_by(SecurityIncident.timestamp.desc()).all()

    # Compter les incidents non résolus pour le badge
    unresolved_count = SecurityIncident.query.filter_by(is_resolved=False).count()

    return render_template(
        "admin/security_incidents.html",
        incidents=incidents,
        status_filter=status_filter,
        unresolved_count=unresolved_count,
    )


# Route 2: Marquer un incident comme résolu
def admin_resolve_incident(incident_id):
    """Marque un incident comme résolu"""
    if current_user.role != "admin":
        return jsonify({"success": False, "error": "Non autorisé"}), 403

    incident = SecurityIncident.query.get_or_404(incident_id)
    incident.is_resolved = True
    incident.resolved_at = datetime.utcnow()
    incident.resolved_by = current_user.id

    db.session.commit()

    flash("Incident marqué comme résolu.", "success")
    return redirect(url_for("admin.security_incidents"))


# Route 3: Ajouter des notes admin
def admin_add_incident_note(incident_id):
    """Ajoute des notes administratives à un incident"""
    if current_user.role != "admin":
        return jsonify({"success": False, "error": "Non autorisé"}), 403

    incident = SecurityIncident.query.get_or_404(incident_id)
    notes = request.form.get("notes", "")

    if notes:
        incident.admin_notes = notes
        db.session.commit()
        flash("Notes ajoutées avec succès.", "success")

    return redirect(url_for("admin.security_incidents"))


# Route 4: API pour obtenir le nombre d'incidents non résolus
def api_unresolved_incidents_count():
    """Retourne le nombre d'incidents non résolus pour le badge"""
    if current_user.role != "admin":
        return jsonify({"count": 0})

    count = SecurityIncident.query.filter_by(is_resolved=False).count()
    return jsonify({"count": count})


# INSTRUCTIONS POUR AJOUTER CES ROUTES À admin.py:
# Ajouter ces décorateurs juste avant chaque fonction dans admin.py:

# @admin_bp.route("/security-incidents")
# @login_required
# def security_incidents():
#     return admin_security_incidents()

# @admin_bp.route("/security-incidents/<int:incident_id>/resolve", methods=["POST"])
# @login_required
# def resolve_incident(incident_id):
#     return admin_resolve_incident(incident_id)

# @admin_bp.route("/security-incidents/<int:incident_id>/add-note", methods=["POST"])
# @login_required
# def add_incident_note(incident_id):
#     return admin_add_incident_note(incident_id)

# @admin_bp.route("/api/security-incidents/count")
# @login_required
# def unresolved_incidents_count():
#     return api_unresolved_incidents_count()
