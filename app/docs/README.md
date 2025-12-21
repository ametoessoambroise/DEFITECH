# 🎓 Application de Gestion d'Étudiants DEFITECH

Une application web complète de gestion d'étudiants pour l'université DEFITECH, développée avec Flask, Python et PostgreSQL.

## ✨ Fonctionnalités

### 🔐 Authentification et Gestion des Utilisateurs

- **Inscription** avec sélection de rôle (Étudiant/Enseignant)
- **Connexion** sécurisée avec hachage des mots de passe
- **Validation** des comptes par l'administration
- **Gestion des rôles** : Administrateur, Enseignant, Étudiant

### 👨‍💼 Dashboard Administration

- **Statistiques** en temps réel (utilisateurs, étudiants, enseignants, filières)
- **Gestion des utilisateurs** (approuver, rejeter, supprimer)
- **Exports** de données (CSV, PDF, JSON)
- **Notifications** système

### 👨‍🏫 Dashboard Enseignant

- **Gestion des notes** par matière et étudiant
- **Suivi des présences** et absences
- **Emploi du temps** des cours
- **Matières enseignées** avec accès restreint

### 👨‍🎓 Dashboard Étudiant

- **Consultation des notes** en lecture seule
- **Emploi du temps** personnel
- **Devoirs et examens** à venir
- **Informations personnelles** complètes

### 📊 Fonctionnalités Avancées

- **Interface responsive** (mobile-first)
- **Exports multiples** (PDF, DOCX, Excel, CSV, JSON)
- **Notifications** par email et alertes internes
- **Gestion des filières** et matières
- **Système de présence** automatisé

## 🛠️ Technologies Utilisées

- **Backend** : Python Flask
- **Base de données** : PostgreSQL
- **Frontend** : HTML5, Tailwind CSS, JavaScript
- **Authentification** : Flask-Login
- **Exports** : ReportLab (PDF), python-docx (DOCX)
- **Icons** : Font Awesome

## 📋 Prérequis

- Python 3.8+
- MySQL 5.7+
- pip (gestionnaire de paquets Python)

## 🚀 Installation

### 1. Cloner le projet

```bash
git clone https://github.com/smiler00/defitech.git
cd DEFITECH
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer la base de données

```bash
python setup_database.py
```

### 4. Lancer l'application

```bash
python app.py
```

### 5. Accéder à l'application

Ouvrez votre navigateur et allez sur : `http://localhost:5000`

## 🔑 Comptes par défaut

### Administrateur

- **Email** : <admin@defitech.com>
- **Mot de passe** : admin123

## 📁 Structure du Projet

```bash
DEFITECH/
├── app.py                 # Application principale Flask
├── setup_database.py      # Script d'initialisation de la BDD
├── requirements.txt       # Dépendances Python
├── README.md             # Documentation
├── static/               # Fichiers statiques
│   ├── css/
│   ├── js/
│   └── assets/
└── templates/            # Templates HTML
    ├── auth/             # Pages d'authentification
    ├── admin/            # Dashboard administration
    ├── enseignant/       # Dashboard enseignant
    └── etudiant/         # Dashboard étudiant
```

## 🗄️ Structure de la Base de Données

### Tables principales

- **user** : Utilisateurs du système
- **etudiant** : Informations spécifiques aux étudiants
- **enseignant** : Informations spécifiques aux enseignants
- **filiere** : Filières de formation
- **matiere** : Matières enseignées
- **note** : Notes des étudiants
- **presence** : Présences et absences
- **emploi_temps** : Planning des cours
- **devoir** : Devoirs et examens

## 🔧 Configuration

### Variables d'environnement

Vous pouvez modifier les paramètres de connexion dans `app.py` :

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://user:password@localhost/defitech_db'
app.config['SECRET_KEY'] = 'votre_cle_secrete'
```

### Personnalisation

- **Couleurs** : Modifiez les classes Tailwind CSS dans les templates
- **Logo** : Remplacez les icônes Font Awesome par votre logo
- **Filières** : Ajoutez vos filières dans `setup_database.py`

## 📱 Interface Mobile

L'application est entièrement responsive et optimisée pour :

- 📱 Smartphones
- 📱 Tablettes
- 💻 Ordinateurs de bureau

## 🔒 Sécurité

- **Mots de passe** hachés avec Werkzeug
- **Sessions** sécurisées avec Flask-Login
- **Validation** des données côté serveur
- **Protection CSRF** intégrée
- **Accès restreint** par rôle

## 📊 Exports Disponibles

### Formats supportés

- **CSV** : Données tabulaires
- **PDF** : Rapports formatés
- **JSON** : Données structurées
- **DOCX** : Documents Word (en développement)

## 🚨 Support et Maintenance

### Logs

Les erreurs sont loggées dans la console Flask.

### Sauvegarde

Effectuez des sauvegardes régulières de la base de données MySQL.

### Mises à jour

1. Sauvegardez votre base de données
2. Mettez à jour le code
3. Exécutez les migrations si nécessaire

## 🤝 Contribution

Pour contribuer au projet :

1. Fork le projet
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Poussez vers la branche
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est développé pour l'université DEFITECH.

## 📞 Contact

Pour toute question ou support :

- **Email** : [smilerambro@gmail.com](mailto:smilerambro@gmail.com)
- **Site web** : [https://defitech.tg](https://defitech.tg)

---

**Développé avec ❤️ pour DEFITECH**
