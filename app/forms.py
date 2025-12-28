"""
Formulaires pour l'application DEFITECH

"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    DateField,
    SelectField,
    SubmitField,
    SelectMultipleField,
    TextAreaField,
    ValidationError,
    FileField,
    HiddenField,
)
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo
from flask_wtf.file import FileField as WTF_FileField, FileAllowed
from werkzeug.utils import secure_filename


class UpdateProfileForm(FlaskForm):
    nom = StringField(
        "Nom",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "Nom"},
    )
    prenom = StringField(
        "Prénom",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "Prénom"},
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "Email"},
    )
    date_naissance = DateField(
        "Date de naissance",
        validators=[DataRequired()],
        render_kw={"placeholder": "Date de naissance"},
    )
    sexe = SelectField(
        "Sexe",
        choices=[
            ("M", "Masculin"),
            ("F", "Féminin"),
            ("Autre", "Gay"),
            ("Autre", "Trans"),
        ],
        validators=[DataRequired()],
    )
    nouveau_mot_de_passe = PasswordField(
        "Nouveau mot de passe",
        validators=[Optional(), Length(min=8)],
        render_kw={"placeholder": "Nouveau mot de passe"},
    )
    confirmer_mot_de_passe = PasswordField(
        "Confirmer le mot de passe",
        validators=[Optional(), EqualTo("nouveau_mot_de_passe")],
        render_kw={"placeholder": "Confirmer le mot de passe"},
    )
    photo_profil = FileField("Photo de profil")
    photo_profil_url = HiddenField("URL Photo de profil")

    # Nouveaux champs pour les informations de contact
    telephone = StringField(
        "Téléphone",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "Téléphone"},
    )
    adresse = StringField(
        "Adresse",
        validators=[Optional(), Length(max=200)],
        render_kw={"placeholder": "Adresse"},
    )
    ville = StringField(
        "Ville",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ville"},
    )
    code_postal = StringField(
        "Code postal",
        validators=[Optional(), Length(max=10)],
        render_kw={"placeholder": "Code postal"},
    )
    pays = StringField(
        "Pays",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Pays"},
    )

    # nouveaux champs pour les liens linkedin, bio et github
    linkedin = StringField(
        "Linkedin",
        validators=[Optional(), Length(max=200)],
        render_kw={
            "placeholder": "https://www.linkedin.com/in/ambroise-ametoesso-587680336/"
        },
    )
    bio = TextAreaField(
        "Bio",
        validators=[Optional(), Length(max=1000, min=20)],
        render_kw={"placeholder": "Je suis un jeune passionné de la tech....."},
    )
    github = StringField(
        "Github",
        validators=[Optional(), Length(max=200)],
        render_kw={"placeholder": "https://github.com/ton_username"},
    )

    # Champs spécifiques aux enseignants
    specialite = StringField(
        "Spécialité",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Spécialité"},
    )
    grade = StringField(
        "Grade",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "Grade"},
    )
    filieres_enseignees = SelectMultipleField(
        "Filières enseignées",
        validators=[Optional()],
        render_kw={"placeholder": "Filières enseignées"},
    )
    annees_enseignees = SelectMultipleField(
        "Années enseignées",
        validators=[Optional()],
        render_kw={"placeholder": "Années enseignées"},
    )
    date_embauche = DateField(
        "Date d'embauche",
        validators=[Optional()],
        render_kw={"placeholder": "Date d'embauche"},
    )

    submit = SubmitField("Valider")


class TeacherProfileApprovalForm(FlaskForm):
    """Formulaire pour l'approbation/rejet des demandes de modification"""

    action = SelectField(
        "Action",
        choices=[("approuve", "Approuver"), ("rejete", "Rejeter")],
        validators=[DataRequired()],
    )
    commentaire_admin = TextAreaField(
        "Commentaire (optionnel)",
        validators=[Optional()],
        render_kw={"placeholder": "Commentaire (optionnel)"},
    )
    submit = SubmitField("Enregistrer")


class BugReportForm(FlaskForm):
    """Formulaire de signalement de bugs"""

    title = StringField(
        "Titre du bug",
        validators=[
            DataRequired(message="Le titre est requis"),
            Length(max=200, message="Le titre ne doit pas dépasser 200 caractères"),
        ],
        render_kw={
            "class": "form-control",
            "placeholder": "Décrivez brièvement le bug",
        },
    )

    description = TextAreaField(
        "Description détaillée",
        validators=[
            DataRequired(message="Veuillez fournir une description détaillée"),
            Length(
                min=20, message="La description doit contenir au moins 20 caractères"
            ),
        ],
        render_kw={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Décrivez le bug de manière détaillée...",
        },
    )

    steps_to_reproduce = TextAreaField(
        "Étapes pour reproduire le bug",
        validators=[
            DataRequired(message="Veuillez indiquer comment reproduire le bug"),
            Length(min=10, message="Veuillez fournir des étapes détaillées"),
        ],
        render_kw={
            "class": "form-control",
            "rows": 4,
            "placeholder": "1. Aller à la page...\n2. Cliquer sur...\n3. Observer que...",
        },
    )

    priority = SelectField(
        "Niveau d'urgence",
        choices=[
            ("low", "Faible - Problème mineur"),
            ("medium", "Moyen - Problème gênant"),
            ("high", "Élevé - Bloque partiellement l'utilisation"),
            ("critical", "Critique - Bloque complètement l'utilisation"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    screenshot = WTF_FileField(
        "Capture d'écran (optionnel)",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "gif"],
                "Seuls les formats d'image sont acceptés (JPG, PNG, GIF)",
            )
        ],
        render_kw={"class": "form-control"},
    )

    submit = SubmitField("Soumettre le rapport", render_kw={"class": "btn btn-primary"})

    def validate_screenshot(self, field):
        if field.data:
            filename = secure_filename(field.data.filename)
            if not (filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))):
                raise ValidationError("Format d'image non pris en charge")


class BugReportAdminForm(BugReportForm):
    """Formulaire d'administration des rapports de bugs"""

    def __init__(self, *args, **kwargs):
        super(BugReportAdminForm, self).__init__(*args, **kwargs)
        # Modifier le bouton de soumission
        self.submit.label.text = "Mettre à jour"

    status = SelectField(
        "Statut",
        choices=[
            ("open", "Ouvert"),
            ("in_progress", "En cours"),
            ("resolved", "Résolu"),
            ("wont_fix", "Ne sera pas corrigé"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    admin_notes = TextAreaField(
        "Notes internes",
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Notes internes sur l'état du bug...",
        },
    )
