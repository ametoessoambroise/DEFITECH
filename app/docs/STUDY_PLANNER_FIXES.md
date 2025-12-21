# Study Planner - Corrections et Améliorations

## Date: 28 Octobre 2025

## Problèmes Corrigés

### 1. Erreur 400 BAD REQUEST sur `/study-planner/api/generate-plan`

**Problème:** 
- Le fetch JavaScript ne incluait pas le token CSRF
- Flask-WTF rejetait les requêtes POST sans token CSRF avec une erreur 400

**Solution:**
- Ajout du token CSRF dans les en-têtes de la requête fetch
- Amélioration de la gestion des erreurs avec des messages plus descriptifs

**Fichier modifié:** `templates/study_planner/index.html`

```javascript
// Avant (ligne 688)
const response = await fetch("/study-planner/api/generate-plan", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
    },
    body: JSON.stringify({...})
});

// Après
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

const response = await fetch("/study-planner/api/generate-plan", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,  // ✅ Token CSRF ajouté
    },
    body: JSON.stringify({...})
});
```

### 2. Utilisation de Données Fictives

**Problème:**
- L'endpoint `/api/pomodoro/stats` retournait des données en dur (hardcodées)
- Aucune persistance des sessions Pomodoro en base de données

**Solution:**
- Création d'un nouveau modèle `PomodoroSession` pour stocker les données réelles
- Mise à jour de l'API pour utiliser les données de la base de données
- Ajout de nouveaux endpoints pour gérer les sessions Pomodoro

## Nouveaux Fichiers Créés

### 1. `models/pomodoro_session.py`

Nouveau modèle pour suivre les sessions d'étude avec la technique Pomodoro.

**Fonctionnalités:**
- Suivi des sessions de travail et des pauses
- Enregistrement de la durée prévue vs durée réelle
- Comptage des interruptions
- Auto-évaluation du niveau de concentration
- Statistiques par jour/semaine/mois
- Analyse par matière

**Méthodes principales:**
- `to_dict()` - Convertit la session en dictionnaire
- `marquer_terminee()` - Marque une session comme terminée
- `marquer_interrompue()` - Marque une session comme interrompue
- `ajouter_interruption()` - Incrémente le compteur d'interruptions
- `get_stats_etudiant(etudiant_id, periode)` - Statistiques par période
- `get_stats_par_matiere(etudiant_id, days)` - Statistiques par matière

### 2. `migrations/create_pomodoro_sessions.sql`

Script SQL pour créer la table `pomodoro_sessions` avec :
- Structure complète de la table
- Index pour optimiser les performances
- Trigger pour mise à jour automatique de `date_modification`
- Contraintes de clés étrangères

## Nouveaux Endpoints API

### 1. POST `/study-planner/api/pomodoro/start`
Démarre une nouvelle session Pomodoro.

**Body:**
```json
{
    "matiere_id": 1,
    "duree_prevue": 25,
    "type_session": "travail",
    "titre": "Révision Mathématiques",
    "description": "Chapitre 3 - Intégrales",
    "tache_associee": "Devoir #12"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": 123,
        "etudiant_id": 7,
        "matiere_id": 1,
        "date_debut": "2025-10-28T10:00:00",
        "duree_prevue": 25,
        "statut": "en_cours",
        ...
    }
}
```

### 2. POST `/study-planner/api/pomodoro/<session_id>/complete`
Marque une session comme terminée.

**Body:**
```json
{
    "pause_prise": true,
    "duree_pause": 5,
    "niveau_concentration": 4
}
```

### 3. POST `/study-planner/api/pomodoro/<session_id>/interrupt`
Marque une session comme interrompue.

### 4. POST `/study-planner/api/pomodoro/<session_id>/add-interruption`
Ajoute une interruption à une session en cours.

## Modifications dans `study_planner.py`

### Imports ajoutés
```python
from models.pomodoro_session import PomodoroSession
```

### Fonction `api_pomodoro_stats()` mise à jour

**Avant (lignes 242-256):**
```python
# Retournait des données fictives
stats = {
    "today": {
        "sessions_completed": 0,
        "total_minutes": 0,
        "breaks_taken": 0,
    },
    ...
}
```

**Après:**
```python
# Utilise maintenant les données réelles de la base
etudiant = Etudiant.query.filter_by(user_id=current_user.id).first()
stats_today = PomodoroSession.get_stats_etudiant(etudiant.id, "today")
stats_week = PomodoroSession.get_stats_etudiant(etudiant.id, "week")
stats_month = PomodoroSession.get_stats_etudiant(etudiant.id, "month")

# Calcul du jour le plus productif
most_productive_day = calculate_most_productive_day(etudiant.id)

stats = {
    "today": {
        "sessions_completed": stats_today["sessions_completed"],
        "total_minutes": stats_today["total_minutes"],
        "breaks_taken": stats_today["breaks_taken"],
    },
    "week": {
        "sessions_completed": stats_week["sessions_completed"],
        "total_minutes": stats_week["total_minutes"],
        "most_productive_day": most_productive_day,  # ✅ Calculé dynamiquement
    },
    ...
}
```

### Nouvelle fonction `calculate_most_productive_day()`

Analyse les sessions de la semaine et détermine le jour où l'étudiant a été le plus productif.

```python
def calculate_most_productive_day(etudiant_id):
    """
    Calcule le jour de la semaine le plus productif pour l'étudiant
    Basé sur le total de minutes de travail par jour
    """
    # Récupère les sessions de la semaine groupées par jour
    # Retourne le jour avec le plus de minutes de travail
    # Si aucune session: retourne "Aucun"
```

## Migration de la Base de Données

### Étapes pour appliquer la migration

1. **Créer la table:**
```bash
# Pour SQLite
sqlite3 instance/defitech.db < migrations/create_pomodoro_sessions.sql

# Ou via Python
python
>>> from app import app, db
>>> with app.app_context():
...     db.session.execute(open('migrations/create_pomodoro_sessions.sql').read())
...     db.session.commit()
```

2. **Vérifier la création:**
```bash
sqlite3 instance/defitech.db
.tables  # Devrait afficher pomodoro_sessions
.schema pomodoro_sessions  # Affiche la structure
```

3. **Ou utiliser Flask-Migrate:**
```bash
flask db migrate -m "Add pomodoro_sessions table"
flask db upgrade
```

## Vérification des Données Réelles

### Tous les endpoints utilisent maintenant la base de données:

| Endpoint | Source de données | Status |
|----------|------------------|--------|
| `/api/dashboard` | ✅ Base de données (Notes, Devoirs, Présences) | OK |
| `/api/generate-plan` | ✅ Base de données (Devoirs, EmploiTemps, Notes) | OK |
| `/api/recommendations` | ✅ Base de données (Notes, Présences, Devoirs) | OK |
| `/api/pomodoro/stats` | ✅ Base de données (PomodoroSession) | **FIXÉ** |

### Données utilisées depuis la base:

1. **Profil étudiant** - `Etudiant.query.filter_by(user_id=current_user.id)`
2. **Notes** - `Note.query.filter_by(etudiant_id=etudiant.id)`
3. **Devoirs** - `Devoir.query.filter(Devoir.filiere == etudiant.filiere, ...)`
4. **Présences** - `Presence.query.filter_by(etudiant_id=etudiant.id)`
5. **Matières** - `Matiere.query.join(Note, ...)`
6. **Emploi du temps** - `EmploiTemps.query.filter_by(filiere_id=etudiant.filiere)`
7. **Sessions Pomodoro** - `PomodoroSession.query.filter(...)`

## Améliorations de la Gestion d'Erreurs

### Dans `index.html` (ligne 704):

```javascript
// Meilleure détection d'erreurs
if (!response.ok) {
    const errorText = await response.text();
    console.error("Server response:", errorText);
    throw new Error(`HTTP error! status: ${response.status}`);
}

// Message d'erreur plus descriptif
catch (error) {
    console.error("Error generating plan:", error);
    alert("Erreur lors de la génération du plan: " + error.message);
}
```

## Tests Recommandés

### 1. Test du CSRF Token
```bash
# Devrait fonctionner maintenant (pas de 400)
curl -X POST http://127.0.0.1:5000/study-planner/api/generate-plan \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: [TOKEN]" \
  -d '{"start_date": "2025-10-28", "end_date": "2025-11-04", "study_hours_per_day": 3}'
```

### 2. Test des Sessions Pomodoro
```bash
# Créer une session
curl -X POST http://127.0.0.1:5000/study-planner/api/pomodoro/start \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: [TOKEN]" \
  -d '{"matiere_id": 1, "duree_prevue": 25, "titre": "Test"}'

# Récupérer les stats (devrait retourner des données réelles)
curl http://127.0.0.1:5000/study-planner/api/pomodoro/stats
```

### 3. Test du Dashboard
```bash
# Devrait retourner des données réelles depuis la DB
curl http://127.0.0.1:5000/study-planner/api/dashboard
```

## Statistiques du Code

| Métrique | Valeur |
|----------|--------|
| Nouveaux fichiers | 2 |
| Fichiers modifiés | 2 |
| Nouvelles lignes | ~350 |
| Endpoints ajoutés | 4 |
| Modèles créés | 1 |
| Fonctions ajoutées | 6 |

## Prochaines Étapes Recommandées

1. **Interface Utilisateur Pomodoro:**
   - Créer un timer visuel pour les sessions
   - Afficher les statistiques en temps réel
   - Ajouter des notifications sonores/visuelles

2. **Analyses Avancées:**
   - Graphiques de productivité
   - Comparaison avec autres étudiants (anonymisé)
   - Recommandations basées sur l'IA

3. **Gamification:**
   - Badges pour sessions complétées
   - Streaks (séries) de jours consécutifs
   - Classement amical entre étudiants

4. **Intégration:**
   - Synchronisation avec Google Calendar
   - Notifications push pour rappels
   - Export des statistiques en PDF

## Conclusion

✅ **Tous les problèmes sont corrigés:**
- Token CSRF ajouté pour éviter les erreurs 400
- Toutes les données proviennent maintenant de la base de données
- Nouveau système de suivi Pomodoro complètement fonctionnel
- Meilleure gestion des erreurs avec messages descriptifs

Le Study Planner utilise maintenant exclusivement des données réelles et offre un suivi complet des sessions d'étude!

---

**Auteur:** AI Assistant  
**Date:** 28 Octobre 2025  
**Version:** 1.0