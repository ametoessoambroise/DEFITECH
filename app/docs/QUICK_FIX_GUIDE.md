# 🚀 Guide Rapide de Correction - DEFITECH Study Planner

## 📋 Résumé des Problèmes Résolus

✅ **Erreur 400 BAD REQUEST** - Corrigée  
✅ **Données fictives** - Remplacées par données réelles  
✅ **Support PostgreSQL** - Ajouté  

## 🔧 Installation en 3 Étapes

### Étape 1 : Appliquer la Migration

Ouvrez un terminal dans le dossier du projet et exécutez :

```bash
python apply_pomodoro_migration.py apply
```

**Ce que fait cette commande :**
- Détecte automatiquement votre type de base de données (PostgreSQL ou SQLite)
- Crée la table `pomodoro_sessions` pour stocker les sessions d'étude
- Crée les index pour optimiser les performances
- Configure les triggers pour la mise à jour automatique

**Sortie attendue :**
```
============================================================
   Migration Pomodoro Sessions - DEFITECH
============================================================

🚀 Début de la migration pomodoro_sessions...
📦 Type de base de données détecté: POSTGRESQL
📊 Exécution de 5 commandes SQL...
   [1/5] Exécution... ✅
   [2/5] Exécution... ✅
   [3/5] Exécution... ✅
   [4/5] Exécution... ✅
   [5/5] Exécution... ✅

✨ Migration terminée avec succès!
✅ Table 'pomodoro_sessions' créée avec succès!

📋 Structure de la table:
   Colonnes:
   - id (INTEGER)
   - etudiant_id (INTEGER)
   - matiere_id (INTEGER)
   - date_debut (TIMESTAMP)
   ...
```

### Étape 2 : Vérifier l'Installation

```bash
python apply_pomodoro_migration.py check
```

**Sortie attendue :**
```
✅ La table 'pomodoro_sessions' existe
📊 Statistiques de la table pomodoro_sessions:
   Total de sessions: 0
```

### Étape 3 : Redémarrer l'Application

```bash
python app.py
```

## ✅ Vérification que Tout Fonctionne

### Test 1 : Accéder au Study Planner
1. Connectez-vous à DEFITECH
2. Allez sur : `http://127.0.0.1:5000/study-planner/`
3. Vous devriez voir votre dashboard sans erreur

### Test 2 : Générer un Plan d'Étude
1. Cliquez sur "Générer un plan d'étude"
2. Remplissez les dates et heures
3. Cliquez sur "Générer le plan"
4. **✅ Pas d'erreur 400** - Le plan se génère correctement

### Test 3 : Vérifier les Données Réelles
1. Ouvrez la console du navigateur (F12)
2. Allez sur l'onglet Network
3. Rechargez la page
4. Cliquez sur la requête `/api/dashboard`
5. Vérifiez que les données correspondent à votre profil

## 🐛 Dépannage

### Problème : "La table existe déjà"

Si vous voyez ce message lors de l'installation :
```
⚠️  La table 'pomodoro_sessions' existe déjà!
```

**Solution :**
```bash
python apply_pomodoro_migration.py rollback
python apply_pomodoro_migration.py apply
```

### Problème : "Erreur de connexion à la base"

**Causes possibles :**
- La base de données n'est pas démarrée
- Les credentials sont incorrects dans `.env`

**Solution :**
1. Vérifiez que PostgreSQL est en cours d'exécution
2. Vérifiez vos variables d'environnement dans `.env` :
```env
SQLALCHEMY_DATABASE_URI=postgresql://user:password@localhost/defitech
```

### Problème : "Module 'psycopg2' not found"

**Solution :**
```bash
pip install psycopg2-binary
```

### Problème : Erreur 400 persiste

**Solution :**
1. Videz le cache du navigateur (Ctrl+Shift+Delete)
2. Rechargez la page avec Ctrl+F5
3. Vérifiez que la balise meta CSRF existe dans le HTML :
```html
<meta name="csrf-token" content="...">
```

## 📊 Commandes Utiles

### Voir les statistiques
```bash
python apply_pomodoro_migration.py stats
```

### Supprimer la table (rollback)
```bash
python apply_pomodoro_migration.py rollback
```

### Réinstaller complètement
```bash
python apply_pomodoro_migration.py rollback
python apply_pomodoro_migration.py apply
```

## 🔍 Vérification Manuelle de la Base de Données

### Pour PostgreSQL

```bash
# Connexion à la base
psql -U votre_utilisateur -d defitech

# Vérifier que la table existe
\dt pomodoro_sessions

# Voir la structure
\d pomodoro_sessions

# Compter les enregistrements
SELECT COUNT(*) FROM pomodoro_sessions;

# Quitter
\q
```

### Pour SQLite (si applicable)

```bash
# Connexion à la base
sqlite3 instance/defitech.db

# Vérifier que la table existe
.tables

# Voir la structure
.schema pomodoro_sessions

# Compter les enregistrements
SELECT COUNT(*) FROM pomodoro_sessions;

# Quitter
.quit
```

## 📝 Fichiers Modifiés

| Fichier | Description | Action |
|---------|-------------|--------|
| `templates/study_planner/index.html` | Ajout du token CSRF | ✅ Modifié |
| `study_planner.py` | Utilisation données DB réelles | ✅ Modifié |
| `models/pomodoro_session.py` | Nouveau modèle | ✅ Créé |
| `migrations/create_pomodoro_sessions_postgresql.sql` | Migration PostgreSQL | ✅ Créé |
| `apply_pomodoro_migration.py` | Script d'installation | ✅ Créé |

## 🎯 Prochaines Étapes

1. ✅ Migration appliquée
2. ✅ Application redémarrée
3. ✅ Tests effectués
4. 🎉 **Profitez du Study Planner !**

## 📚 Documentation Complète

Pour plus de détails, consultez :
- [`STUDY_PLANNER_FIXES.md`](STUDY_PLANNER_FIXES.md) - Documentation technique complète
- [`README_STUDY_PLANNER.md`](README_STUDY_PLANNER.md) - Guide utilisateur détaillé

## 💡 Astuces

### Astuce 1 : Créer des Données de Test
Pour tester le système avec des données :
```python
python
>>> from app import app, db
>>> from models.pomodoro_session import PomodoroSession
>>> from models.etudiant import Etudiant
>>> 
>>> with app.app_context():
...     etudiant = Etudiant.query.first()
...     session = PomodoroSession(
...         etudiant_id=etudiant.id,
...         duree_prevue=25,
...         titre="Test Session"
...     )
...     db.session.add(session)
...     db.session.commit()
...     print("Session créée!")
```

### Astuce 2 : Surveiller les Logs
```bash
# Dans un terminal séparé
tail -f instance/defitech.log
```

### Astuce 3 : Mode Debug
Activez le mode debug dans `.env` :
```env
FLASK_DEBUG=1
```

## ❓ FAQ

**Q : Les anciennes sessions Pomodoro sont-elles perdues ?**  
R : Non, la migration crée simplement une nouvelle table. Les anciennes données (si elles existaient ailleurs) restent intactes.

**Q : Puis-je annuler la migration ?**  
R : Oui, utilisez `python apply_pomodoro_migration.py rollback`

**Q : Le système fonctionne-t-il hors ligne ?**  
R : Oui, une fois les données chargées, le Study Planner peut fonctionner localement.

**Q : Combien d'espace disque est nécessaire ?**  
R : La table `pomodoro_sessions` occupe environ 1-2 MB pour 1000 sessions.

## 🆘 Support

Si vous rencontrez des problèmes :

1. **Vérifiez les logs** : `instance/defitech.log`
2. **Console navigateur** : F12 → Console
3. **Réessayez** : Rechargez avec Ctrl+F5
4. **Contactez le support** : support@defitech.com

## ✨ Améliorations Apportées

| Fonctionnalité | Avant | Après |
|----------------|-------|-------|
| Token CSRF | ❌ Manquant | ✅ Présent |
| Données Pomodoro | ❌ Fictives | ✅ Réelles (DB) |
| Support PostgreSQL | ❌ SQLite seulement | ✅ PostgreSQL + SQLite |
| Statistiques | ❌ Hardcodées (0) | ✅ Calculées dynamiquement |
| API Complète | ❌ Limitée | ✅ 4 nouveaux endpoints |

## 🎉 Félicitations !

Si vous êtes arrivé jusqu'ici et que tout fonctionne, bravo ! 🎊

Le Study Planner est maintenant entièrement fonctionnel avec des données réelles.

Bon courage pour vos études ! 📚✨

---

**Version :** 1.0  
**Date :** 28 Octobre 2025  
**Auteur :** DEFITECH Team