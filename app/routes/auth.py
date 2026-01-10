from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
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
        if request.is_json:
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")
        else:
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
                    print("✅ Connexion réussie")

                    if request.is_json:
                        return jsonify(
                            {
                                "success": True,
                                "message": "Connexion réussie",
                                "user": {
                                    "id": user.id,
                                    "nom": user.nom,
                                    "prenom": user.prenom,
                                    "email": user.email,
                                    "role": user.role,
                                    "photo_profil": user.photo_profil,
                                },
                            }
                        )

                    flash("Connexion réussie.", "success")

                    # Vérifier s'il y a un paramètre 'next' pour la redirection
                    next_page = request.args.get("next")
                    # Basic open redirect protection
                    if next_page and next_page.startswith("/"):
                        return redirect(next_page)
                    if user.role == "admin":
                        return redirect(url_for("admin.dashboard"))
                    elif user.role == "etudiant":
                        return redirect(url_for("students.dashboard"))
                    elif user.role == "enseignant":
                        return redirect(url_for("teachers.dashboard"))
                    else:
                        return redirect(url_for("main.index"))
                else:
                    if request.is_json:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "message": "Votre compte est en attente d'approbation.",
                                }
                            ),
                            401,
                        )

                    flash(
                        "Votre compte est en attente d'approbation par l'administration.",
                        "warning",
                    )
                    print("⚠️ Compte en attente d'approbation")
            else:
                if request.is_json:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "Email ou mot de passe incorrect.",
                            }
                        ),
                        401,
                    )

                flash("Email ou mot de passe incorrect.", "error")
                print("❌ Mot de passe incorrect")
        else:
            if request.is_json:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Email ou mot de passe incorrect.",
                        }
                    ),
                    401,
                )

            flash("Email ou mot de passe incorrect.", "error")
            print("❌ Utilisateur non trouvé")

    # Si c'est une requête JSON mais pas POST (erreur méthode) ou autre cas
    if request.is_json:
        return jsonify({"success": False, "message": "Méthode non autorisée"}), 405

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

        # Champs spécifiques Étudiant
        lieu_naissance = request.form.get("lieu_naissance")
        nationalite = request.form.get("nationalite")
        bac_serie = request.form.get("bac_serie")
        bac_annee = request.form.get("bac_annee")
        etablissement_provenance = request.form.get("etablissement_provenance")
        filiere = request.form.get("filiere")
        annee = request.form.get("annee")

        # Champs spécifiques Parent
        parent_nom = request.form.get("parent_nom")
        parent_prenom = request.form.get("parent_prenom")
        parent_profession = request.form.get("parent_profession")
        parent_organisme = request.form.get("parent_organisme")
        parent_adresse = request.form.get("parent_adresse")
        parent_tel_bur = request.form.get("parent_tel_bur")
        parent_tel_dom = request.form.get("parent_tel_dom")
        parent_email = request.form.get("parent_email")

        # Champs spécifiques Paiement
        modalite_paiement = request.form.get("modalite_paiement")
        autres_modalites = request.form.get("autres_modalites")
        modalites_choisies = request.form.get("modalites_choisies")

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
                lieu_naissance=lieu_naissance,
                nationalite=nationalite,
                bac_serie=bac_serie,
                bac_annee=bac_annee,
                etablissement_provenance=etablissement_provenance,
                modalite_paiement=modalite_paiement,
                autres_modalites=autres_modalites,
                modalites_choisies=modalites_choisies,
            )
            db.session.add(etudiant)
            db.session.flush()  # Pour avoir l'id de l'étudiant

            # Créer le profil Parent
            if parent_nom and parent_prenom:
                from app.models.parent import Parent

                parent = Parent(
                    etudiant_id=etudiant.id,
                    nom=parent_nom,
                    prenom=parent_prenom,
                    profession=parent_profession,
                    organisme_employeur=parent_organisme,
                    adresse=parent_adresse,
                    tel_bureau=parent_tel_bur,
                    tel_domicile=parent_tel_dom,
                    email=parent_email,
                )
                db.session.add(parent)

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

        # Si parent, lier à l'étudiant via le code
        elif role == "parent":
            parent_code = request.form.get("parent_code")
            if not parent_code:
                # Si le code est manquant, on supprime l'utilisateur créé pour éviter les orphelins
                db.session.delete(user)
                db.session.commit()
                flash("Le code d'accès parent est obligatoire.", "error")
                return render_template(
                    "auth/register.html", filieres=filieres, annees=annees
                )

            # Trouver l'étudiant par son code
            etudiant_target = Etudiant.query.filter_by(code_parent=parent_code).first()
            if not etudiant_target:
                db.session.delete(user)
                db.session.commit()
                flash("Code d'accès parent invalide.", "error")
                return render_template(
                    "auth/register.html", filieres=filieres, annees=annees
                )

            # Créer ou mettre à jour l'enregistrement Parent
            from app.models.parent import Parent

            # On cherche s'il y a déjà un parent pour cet étudiant avec cet email
            p_record = Parent.query.filter_by(
                etudiant_id=etudiant_target.id, email=user.email
            ).first()
            if not p_record:
                # Créer un nouvel enregistrement Parent lié à l'utilisateur
                p_record = Parent(
                    etudiant_id=etudiant_target.id,
                    nom=user.nom,
                    prenom=user.prenom,
                    email=user.email,
                    user_id=user.id,
                )
                db.session.add(p_record)
            else:
                p_record.user_id = user.id

            # Invalider le code après utilisation (usage unique)
            etudiant_target.code_parent = None
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
