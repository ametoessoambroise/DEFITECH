from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, timedelta, UTC
import re
import secrets
import json

from app.extensions import db
from app.models.user import User
from app.models.etudiant import Etudiant
from app.models.enseignant import Enseignant
from app.models.filiere import Filiere
from app.models.annee import Annee
from app.models.password_reset_token import PasswordResetToken
from app.email_utils import send_confirmation_email, send_password_reset_email

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Page de connexion.
    """
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        print(f"🔍 Tentative de connexion pour: {email}")

        user = User.query.filter_by(email=email).first()

        if user:
            print(f"✅ Utilisateur trouvé: {user.nom} {user.prenom}")
            print(f"📋 Rôle: {user.role}, Statut: {user.statut}")

            if check_password_hash(user.password_hash, password):
                print("✅ Mot de passe correct")
                if user.statut == "approuve":
                    login_user(user)
                    flash("Connexion réussie.", "success")
                    print("✅ Connexion réussie")

                    # Vérifier s'il y a un paramètre 'next' pour la redirection
                    next_page = request.args.get("next")
                    # Basic open redirect protection
                    if next_page and next_page.startswith("/"):
                        return redirect(next_page)
                    if user.role == 'admin':
                        return redirect(url_for("admin.dashboard"))
                    elif user.role == 'etudiant':
                        return redirect(url_for("students.dashboard"))
                    elif user.role == 'enseignant':
                        return redirect(url_for("teachers.dashboard"))
                    else:
                        return redirect(url_for("main.index"))
                else:
                    flash(
                        "Votre compte est en attente d'approbation par l'administration.",
                        "warning",
                    )
                    print("⚠️ Compte en attente d'approbation")
            else:
                flash("Email ou mot de passe incorrect.", "error")
                print("❌ Mot de passe incorrect")
        else:
            flash("Email ou mot de passe incorrect.", "error")
            print("❌ Utilisateur non trouvé")

    return render_template("auth/login.html", current_year=datetime.now().year)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Page d'inscription d'un utilisateur.
    """
    filieres = Filiere.query.all()
    annees = Annee.query.all()

    # Récupérer toutes les filières disponibles pour les enseignants
    filieres_enseignees = sorted([filiere.nom for filiere in filieres])

    # Récupérer toutes les années disponibles pour les enseignants
    annees_enseignement = sorted([annee.nom for annee in annees])

    if request.method == "POST":
        if not request.form:
            return "Aucune donnée de formulaire reçue", 400
        nom = request.form["nom"]
        prenom = request.form["prenom"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]
        date_naissance = datetime.strptime(
            request.form["date_naissance"], "%Y-%m-%d"
        ).date()
        sexe = request.form["sexe"]

        # Champs spécifiques
        filiere = request.form.get("filiere")
        annee = request.form.get("annee")
        filieres_enseignees_form = request.form.getlist("filieres_enseignees")
        annees_enseignant = request.form.getlist("annees_enseignant")

        # Validation email
        email_regex = r"^([\w\.-]+)@([\w\.-]+)\.([a-zA-Z]{2,})$"
        if not re.match(email_regex, email):
            flash("Veuillez saisir une adresse email valide.", "error")
            return render_template(
                "auth/register.html", filieres=filieres, annees=annees
            )
        # Validation mot de passe fort
        if (
            len(password) < 8
            or not re.search(r"[A-Z]", password)
            or not re.search(r"[a-z]", password)
            or not re.search(r"\d", password)
            or not re.search(r"[^A-Za-z0-9]", password)
        ):
            flash(
                "Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule, un chiffre et un caractère spécial.",
                "error",
            )
            return render_template(
                "auth/register.html", filieres=filieres, annees=annees
            )

        # Calculer l'âge
        today = date.today()
        age = (
            today.year
            - date_naissance.year
            - ((today.month, today.day) < (date_naissance.month, date_naissance.day))
        )

        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "error")
            return render_template(
                "auth/register.html", filieres=filieres, annees=annees
            )

        # Créer l'utilisateur
        user = User(
            nom=nom,
            prenom=prenom,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            date_naissance=date_naissance,
            sexe=sexe,
            age=age,
            date_creation=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.commit()

        # Envoi de l'email de confirmation
        send_confirmation_email(user)

        # Si étudiant, créer le profil Etudiant
        if role == "etudiant" and filiere and annee:
            # Générer un numéro d'étudiant unique basé sur l'année et un nombre aléatoire
            import random

            while True:
                # Format: DEFI + 5 chiffres aléatoires
                new_numero = f"DEFI{random.randint(10000, 99999)}"
                # Vérifier si le numéro existe déjà
                if not Etudiant.query.filter_by(numero_etudiant=new_numero).first():
                    break
            etudiant = Etudiant(
                user_id=user.id,
                filiere=filiere,
                annee=annee,
                numero_etudiant=new_numero,
            )
            db.session.add(etudiant)
            db.session.commit()
        # Si enseignant, créer le profil Enseignant
        elif role == "enseignant" and filieres_enseignees_form and annees_enseignant:
            enseignant = Enseignant(
                user_id=user.id,
                specialite="",
                filieres_enseignees=json.dumps(
                    {"filieres": filieres_enseignees_form, "annees": annees_enseignant}
                ),
            )
            db.session.add(enseignant)
            db.session.commit()

        flash(
            "Inscription réussie. Votre compte sera approuvé par l'administration.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/register.html",
        filieres=filieres,
        annees=annees,
        filieres_enseignees=filieres_enseignees,
        annees_enseignement=annees_enseignement,
    )


@auth_bp.route("/logout")
@login_required
def logout():
    """
    Déconnecte l'utilisateur actuel et redirige vers la page de connexion.
    """
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    Permet de réinitialiser le mot de passe d'un utilisateur.
    """
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            # Créer un jeton de réinitialisation
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(UTC) + timedelta(hours=1)  # Lien valide 1 heure

            # Désactiver les anciens jetons
            PasswordResetToken.query.filter_by(user_id=user.id).update(
                {"is_used": True}
            )
            reset_token = PasswordResetToken(
                user_id=user.id, token=token, expires_at=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()

            # Envoyer l'email
            if send_password_reset_email(user, token):
                flash(
                    "Un email de réinitialisation a été envoyé à votre adresse email.",
                    "info",
                )

            else:
                flash(
                    "Une erreur est survenue lors de l'envoi de l'email. Veuillez réessayer plus tard.",
                    "error",
                )
        else:
            # Pour des raisons de sécurité, on ne révèle pas si l'email existe ou non
            flash(
                "Si votre adresse email existe dans notre système, vous recevrez un email de réinitialisation.",
                "info",
            )

        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    Permet de réinitialiser le mot de passe d'un utilisateur via un lien envoyé par email.
    """
    reset_token = PasswordResetToken.query.filter_by(token=token, is_used=False).first()

    if not reset_token or not reset_token.is_valid():
        flash("Le lien de réinitialisation est invalide ou a expiré.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "error")
            return redirect(request.url)

        # Mettre à jour le mot de passe
        user = User.query.get(reset_token.user_id)
        user.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

        # Marquer le jeton comme utilisé
        reset_token.is_used = True

        db.session.commit()

        flash(
            "Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)
