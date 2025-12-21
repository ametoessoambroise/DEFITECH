"""
Modèle pour les compétences des utilisateurs
"""
from app.extensions import db

class Competence(db.Model):
    __tablename__ = 'competences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    niveau = db.Column(db.String(50))  # débutant, intermédiaire, avancé, expert
    categorie = db.Column(db.String(50))  # technique, linguistique, etc.
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), 
                         onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'niveau': self.niveau,
            'categorie': self.categorie,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
