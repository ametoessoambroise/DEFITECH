from app.extensions import db
from datetime import datetime


class NoteModificationRequest(db.Model):
    """
    Modèle pour gérer les demandes de modification de notes par les enseignants.
    """

    __tablename__ = "note_modification_request"

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("note.id"), nullable=False)
    enseignant_id = db.Column(
        db.Integer, db.ForeignKey("enseignant.id"), nullable=False
    )
    nouvelle_valeur = db.Column(db.Float, nullable=False)
    raison = db.Column(db.Text, nullable=False)
    statut = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    date_demande = db.Column(db.DateTime, default=datetime.utcnow)
    date_traitement = db.Column(db.DateTime, nullable=True)

    # Relations
    note = db.relationship(
        "Note", backref=db.backref("modification_requests", lazy=True)
    )
    enseignant = db.relationship(
        "Enseignant", backref=db.backref("demandes_modification", lazy=True)
    )

    def __repr__(self):
        return (
            f"<NoteModificationRequest {self.id} - Note {self.note_id} - {self.statut}>"
        )
