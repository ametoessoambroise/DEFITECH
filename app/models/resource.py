"""
Modèle pour les ressources numériques (livres PDF, cours, etc.)

Ce modèle permet aux enseignants de partager des ressources numériques
avec les étudiants de leur filière et année.
"""

from datetime import datetime
from app.extensions import db
import os


class Resource(db.Model):
    """Modèle pour les ressources numériques"""

    __tablename__ = "resource"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    nom_fichier = db.Column(db.String(255), nullable=False)
    chemin_fichier = db.Column(db.String(500), nullable=False)
    type_fichier = db.Column(db.String(50), nullable=False)  # pdf, docx, pptx, etc.
    taille = db.Column(db.Integer, nullable=False)  # Taille en octets
    type_ressource = db.Column(
        db.String(50), nullable=False
    )  # livre, cours, td, tp, etc.
    matiere_id = db.Column(db.Integer, db.ForeignKey("matiere.id"), nullable=True)
    filiere = db.Column(db.String(100), nullable=False)
    annee = db.Column(db.String(100), nullable=False)
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    enseignant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Relations
    matiere = db.relationship("Matiere", backref=db.backref("resources", lazy=True))
    enseignant = db.relationship(
        "User", backref=db.backref("uploaded_resources", lazy=True)
    )

    def __repr__(self):
        return f"<Resource {self.id} - {self.titre}>"

    @property
    def extension(self):
        """Retourne l'extension du fichier"""
        return (
            self.nom_fichier.rsplit(".", 1)[1].lower()
            if "." in self.nom_fichier
            else ""
        )

    @property
    def taille_formattee(self):
        """Retourne la taille du fichier formatée"""
        taille = self.taille
        if taille < 1024:
            return f"{taille} B"
        elif taille < 1024 * 1024:
            return f"{taille // 1024} KB"
        elif taille < 1024 * 1024 * 1024:
            return f"{taille // (1024 * 1024)} MB"
        else:
            return f"{taille // (1024 * 1024 * 1024)} GB"

    @property
    def icone_type(self):
        """Retourne l'icône selon le type de fichier"""
        icons = {
            "pdf": "fas fa-file-pdf",
            "docx": "fas fa-file-word",
            "doc": "fas fa-file-word",
            "pptx": "fas fa-file-powerpoint",
            "ppt": "fas fa-file-powerpoint",
            "xlsx": "fas fa-file-excel",
            "xls": "fas fa-file-excel",
            "txt": "fas fa-file-alt",
            "zip": "fas fa-file-archive",
            "rar": "fas fa-file-archive",
            "7z": "fas fa-file-archive",
        }
        return icons.get(self.extension, "fas fa-file")

    @property
    def couleur_type(self):
        """Retourne la couleur selon le type de fichier"""
        colors = {
            "pdf": "red",
            "docx": "blue",
            "doc": "blue",
            "pptx": "orange",
            "ppt": "orange",
            "xlsx": "green",
            "xls": "green",
            "txt": "gray",
            "zip": "purple",
            "rar": "purple",
            "7z": "purple",
        }
        return colors.get(self.extension, "gray")

    @classmethod
    def get_resources_for_user(cls, user):
        """Récupère les ressources accessibles par un utilisateur"""
        if user.role == "admin":
            return cls.query.order_by(cls.date_upload.desc()).all()
        elif user.role == "etudiant":
            # Les étudiants ne voient que les ressources de leur filière et année
            from app.models.etudiant import Etudiant

            etudiant = Etudiant.query.filter_by(user_id=user.id).first()
            if etudiant:
                return (
                    cls.query.filter_by(filiere=etudiant.filiere, annee=etudiant.annee)
                    .order_by(cls.date_upload.desc())
                    .all()
                )
            return []
        else:  # enseignant
            # Les enseignants voient toutes les ressources de leurs filières
            from app.models.enseignant import Enseignant

            enseignant = Enseignant.query.filter_by(user_id=user.id).first()
            if enseignant:
                # Récupérer les filières enseignées
                filieres = []
                if enseignant.filieres_enseignees:
                    import json

                    data = json.loads(enseignant.filieres_enseignees)
                    filieres = data.get("filieres", [])

                if filieres:
                    return (
                        cls.query.filter(cls.filiere.in_(filieres))
                        .order_by(cls.date_upload.desc())
                        .all()
                    )
            return []

    @classmethod
    def search_resources(
        cls, query, filiere=None, annee=None, type_ressource=None, matiere_id=None
    ):
        """Recherche dans les ressources"""
        search_query = cls.query

        if query:
            search_query = search_query.filter(
                db.or_(
                    cls.titre.ilike(f"%{query}%"),
                    cls.description.ilike(f"%{query}%"),
                    cls.nom_fichier.ilike(f"%{query}%"),
                )
            )

        if filiere:
            search_query = search_query.filter_by(filiere=filiere)

        if annee:
            search_query = search_query.filter_by(annee=annee)

        if type_ressource:
            search_query = search_query.filter_by(type_ressource=type_ressource)

        if matiere_id:
            search_query = search_query.filter_by(matiere_id=matiere_id)

        return search_query.order_by(cls.date_upload.desc()).all()

    def delete_file(self):
        """Supprime le fichier physique s'il est local"""
        if self.chemin_fichier.startswith(("http://", "https://")):
            # On pourrait supprimer de Cloudinary ici, mais on se contente de ne pas lever d'erreur locale
            return True

        try:
            if os.path.exists(self.chemin_fichier):
                os.remove(self.chemin_fichier)
                return True
        except Exception as e:
            print(f"Erreur suppression fichier local {self.chemin_fichier}: {e}")
        return False
