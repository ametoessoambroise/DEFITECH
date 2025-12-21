# 📚 Guide d'Utilisation - Study Planner (Planificateur d'Études)

## 🎯 Vue d'ensemble

Le **Study Planner** est un outil intelligent de planification d'études qui utilise l'intelligence artificielle pour aider les étudiants à organiser leur temps d'étude de manière optimale.

## ✨ Fonctionnalités Principales

### 1. Tableau de Bord Personnalisé
- **Statistiques de performance** : moyenne générale, taux de présence, nombre de notes
- **Devoirs à venir** : liste des devoirs urgents et non consultés
- **Matières faibles** : identification automatique des matières nécessitant plus d'attention
- **Temps d'étude recommandé** : calcul intelligent basé sur vos performances

### 2. Générateur de Plan d'Étude Intelligent
Le système génère automatiquement un plan d'étude personnalisé en tenant compte de :
- ✅ Vos devoirs urgents (moins de 3 jours avant la date limite)
- ✅ Vos matières faibles (moyenne < 12/20)
- ✅ Votre emploi du temps (pour éviter les conflits)
- ✅ Votre charge de travail optimale

### 3. Technique Pomodoro Intégrée
- ⏱️ Sessions de travail de 25 minutes
- ☕ Pauses courtes de 5 minutes
- 🛋️ Pauses longues de 15 minutes
- 📊 Statistiques de productivité en temps réel

### 4. Recommandations Personnalisées
L'IA analyse vos données et fournit des recommandations sur :
- Les matières à prioriser
- Les techniques d'apprentissage adaptées
- La gestion du temps
- Les habitudes d'étude efficaces

## 🚀 Démarrage Rapide

### Prérequis
- Compte étudiant actif sur DEFITECH
- Connexion à Internet
- Navigateur web moderne (Chrome, Firefox, Edge)

### Accès au Study Planner
1. Connectez-vous à votre compte DEFITECH
2. Cliquez sur **"Study Planner"** dans le menu principal
3. Vous serez redirigé vers votre tableau de bord personnalisé

## 📖 Guide d'Utilisation Détaillé

### Étape 1 : Consulter votre Dashboard
Au premier lancement, le dashboard affiche :
- Vos statistiques académiques actuelles
- Les devoirs à venir dans les prochains jours
- Vos 3 matières les plus faibles
- Le temps d'étude recommandé par jour

### Étape 2 : Générer un Plan d'Étude

#### 2.1 Ouvrir le formulaire de génération
Cliquez sur le bouton **"Générer un plan d'étude"**

#### 2.2 Configurer les paramètres
- **Date de début** : Quand voulez-vous commencer ?
- **Date de fin** : Jusqu'à quand souhaitez-vous planifier ?
- **Heures par jour** : Combien d'heures pouvez-vous consacrer à l'étude quotidiennement ?
  - Minimum : 1 heure
  - Maximum : 8 heures
  - Recommandé : 3-4 heures

#### 2.3 Générer le plan
Cliquez sur **"Générer le plan"**. Le système va :
1. Analyser vos devoirs urgents
2. Identifier vos matières faibles
3. Vérifier votre emploi du temps
4. Créer un planning optimal
5. Ajouter des pauses Pomodoro

#### 2.4 Consulter votre plan
Le plan généré contient pour chaque jour :
- 📅 Date et jour de la semaine
- ⏰ Sessions d'étude avec horaires
- 📚 Matières à travailler
- 🎯 Objectifs spécifiques
- ☕ Pauses recommandées
- ⏱️ Durée totale d'étude

### Étape 3 : Utiliser le Timer Pomodoro

#### 3.1 Démarrer une session
1. Choisissez une matière dans votre plan
2. Cliquez sur **"Démarrer Pomodoro"**
3. Le timer de 25 minutes commence

#### 3.2 Pendant la session
- 🎯 Concentrez-vous uniquement sur la tâche
- 🚫 Évitez toutes distractions
- 📝 Notez les interruptions si nécessaire

#### 3.3 Prendre une pause
Après chaque session :
- Pause courte (5 min) après 1-3 sessions
- Pause longue (15 min) après 4 sessions

#### 3.4 Suivre vos statistiques
Consultez vos stats Pomodoro :
- Nombre de sessions complétées
- Total de minutes d'étude
- Jour le plus productif
- Moyenne par jour

## 🔧 Fonctionnalités Avancées

### API REST pour Développeurs

Le Study Planner expose plusieurs endpoints API :

#### 1. Récupérer le Dashboard
```
GET /study-planner/api/dashboard
```
Retourne toutes les statistiques de l'étudiant.

#### 2. Générer un Plan
```
POST /study-planner/api/generate-plan
Headers: X-CSRFToken: <token>
Body: {
  "start_date": "2025-10-28",
  "end_date": "2025-11-04",
  "study_hours_per_day": 3,
  "focus_areas": ["Mathématiques", "Physique"]
}
```

#### 3. Statistiques Pomodoro
```
GET /study-planner/api/pomodoro/stats
```
Retourne les stats aujourd'hui/semaine/mois.

#### 4. Démarrer une Session Pomodoro
```
POST /study-planner/api/pomodoro/start
Headers: X-CSRFToken: <token>
Body: {
  "matiere_id": 1,
  "duree_prevue": 25,
  "titre": "Révision Chapitre 3"
}
```

#### 5. Terminer une Session
```
POST /study-planner/api/pomodoro/<session_id>/complete
Headers: X-CSRFToken: <token>
Body: {
  "pause_prise": true,
  "duree_pause": 5,
  "niveau_concentration": 4
}
```

#### 6. Marquer une Interruption
```
POST /study-planner/api/pomodoro/<session_id>/add-interruption
Headers: X-CSRFToken: <token>
```

### Base de Données - Table PomodoroSession

#### Structure
```sql
CREATE TABLE pomodoro_sessions (
    id INTEGER PRIMARY KEY,
    etudiant_id INTEGER NOT NULL,
    matiere_id INTEGER,
    date_debut DATETIME NOT NULL,
    date_fin DATETIME,
    duree_prevue INTEGER DEFAULT 25,
    duree_reelle INTEGER,
    type_session VARCHAR(20) DEFAULT 'travail',
    statut VARCHAR(20) DEFAULT 'en_cours',
    titre VARCHAR(200),
    description TEXT,
    pause_prise BOOLEAN DEFAULT 0,
    nombre_interruptions INTEGER DEFAULT 0,
    niveau_concentration INTEGER
);
```

#### Types de Statut
- `en_cours` : Session actuellement en cours
- `terminee` : Session complétée avec succès
- `interrompue` : Session arrêtée prématurément

#### Types de Session
- `travail` : Session de travail/étude
- `pause` : Session de pause

## 📊 Algorithmes d'IA

### 1. Analyse des Matières Faibles
L'algorithme identifie les matières nécessitant plus d'attention :
```
Si moyenne < 12/20 → Matière faible
Si moyenne < 10/20 → Très difficile
Si moyenne < 8/20 → Critique

Priorité = (12 - moyenne) × 10 + min(nb_notes × 5, 30)
```

### 2. Calcul du Temps d'Étude Recommandé
```
Temps de base : 120 minutes (2h)

Ajustements :
+ Si moyenne < 10 : +60 min
+ Si moyenne < 12 : +30 min
+ Par devoir urgent : +15 min
+ Par matière faible : +20 min

Maximum : 300 minutes (5h)
```

### 3. Distribution du Temps d'Étude
Priorités dans l'ordre :
1. 🔴 **Devoirs urgents** (< 3 jours) : Max 60 min/session
2. 🟡 **Matières faibles** : Top 3 matières, 45 min chacune
3. 🟢 **Zones de focus** : Matières choisies, 45 min
4. 🔵 **Révision générale** : Temps restant

### 4. Pauses Intelligentes
```
Si session < 30 min → Pause de 5 min
Si session ≥ 30 min → Pause de 15 min
Après 4 sessions → Pause longue de 30 min
```

## 💡 Conseils d'Utilisation

### Pour Maximiser votre Efficacité

#### ✅ À FAIRE
- 📅 Planifiez votre semaine le dimanche soir
- ⏰ Étudiez aux heures où vous êtes le plus concentré
- 🎯 Fixez des objectifs clairs pour chaque session
- 📝 Prenez des notes pendant vos sessions
- ☕ Respectez les pauses recommandées
- 📊 Consultez vos statistiques régulièrement
- 🔄 Ajustez votre plan si nécessaire

#### ❌ À ÉVITER
- 📱 Utiliser votre téléphone pendant les sessions
- 🎮 Ouvrir les réseaux sociaux
- 🏃 Sauter les pauses (risque de burnout)
- 😴 Étudier en étant fatigué
- 🎲 Étudier sans plan
- ⏰ Remettre à demain

### Techniques Complémentaires

#### 1. La Méthode Feynman
Expliquez la matière comme si vous l'enseigniez à un enfant de 10 ans.

#### 2. Le Rappel Actif
Testez-vous régulièrement sans regarder vos notes.

#### 3. La Répétition Espacée
Révisez la matière à intervalles croissants (1j, 3j, 7j, 14j).

#### 4. La Technique Cornell
Prenez des notes en 3 sections : notes, indices, résumé.

## 🐛 Dépannage

### Problème : Le plan ne se génère pas

**Causes possibles :**
- Dates invalides (date de fin avant date de début)
- Pas de connexion Internet
- Session expirée

**Solutions :**
1. Vérifiez vos dates
2. Rechargez la page (F5)
3. Reconnectez-vous
4. Videz le cache du navigateur

### Problème : Statistiques à 0

**Causes :**
- Première utilisation (pas encore de données)
- Table non créée en base de données

**Solutions :**
1. Utilisez le timer Pomodoro pour générer des données
2. Vérifiez que la migration est appliquée :
```bash
python apply_pomodoro_migration.py check
```

### Problème : Erreur 400 (Bad Request)

**Cause :** Token CSRF manquant ou invalide

**Solutions :**
1. Rechargez la page complètement (Ctrl+F5)
2. Vérifiez que la meta tag CSRF existe dans le HTML
3. Déconnectez-vous et reconnectez-vous

### Problème : Recommandations non pertinentes

**Causes :**
- Pas assez de données historiques
- Notes non à jour

**Solutions :**
1. Utilisez le système pendant au moins 1 semaine
2. Assurez-vous que vos notes sont bien enregistrées
3. Vérifiez que vos devoirs sont bien renseignés

## 📈 Statistiques et Analyses

### Métriques Disponibles

#### Performance Académique
- Moyenne générale
- Taux de présence
- Nombre de notes
- Évolution mensuelle

#### Productivité
- Sessions Pomodoro complétées
- Total de minutes d'étude
- Pauses prises
- Interruptions
- Niveau de concentration moyen

#### Matières
- Temps par matière (7 derniers jours)
- Progression par matière
- Matières les plus travaillées

#### Tendances
- Jour le plus productif
- Heure préférée d'étude
- Évolution hebdomadaire
- Comparaison mois par mois

## 🔐 Confidentialité et Sécurité

### Protection des Données
- ✅ Toutes vos données sont chiffrées
- ✅ Seul vous avez accès à vos statistiques
- ✅ Pas de partage avec des tiers
- ✅ Conformité RGPD

### Contrôle Parental
Les parents/tuteurs peuvent demander un accès aux statistiques via l'administration.

## 🆘 Support et Assistance

### Besoin d'Aide ?

#### Documentation
- 📚 [Guide complet](STUDY_PLANNER_FIXES.md)
- 🔧 [Documentation technique](README.md)
- 💻 [API Reference](API_DOCS.md)

#### Contact
- 📧 Email : support@defitech.com
- 💬 Chat : disponible dans l'application
- 📞 Téléphone : +XXX XXX XXX XXX

#### Signaler un Bug
1. Allez sur GitHub Issues
2. Décrivez le problème en détail
3. Joignez des captures d'écran si possible
4. Mentionnez votre navigateur et version

## 🎓 Ressources Supplémentaires

### Articles Recommandés
- 📖 "La Technique Pomodoro Expliquée"
- 📖 "10 Conseils pour Mieux Étudier"
- 📖 "Comment Gérer son Temps Efficacement"

### Vidéos Tutorielles
- 🎥 "Introduction au Study Planner" (5 min)
- 🎥 "Générer son Premier Plan d'Étude" (10 min)
- 🎥 "Maîtriser la Technique Pomodoro" (8 min)

### Communauté
- 👥 Forum DEFITECH : Échangez avec d'autres étudiants
- 📱 Groupe WhatsApp : Entraide entre étudiants
- 🎮 Discord : Séances d'étude en groupe

## 📅 Feuille de Route

### Version Actuelle : v1.0
- ✅ Génération de plans d'étude
- ✅ Timer Pomodoro
- ✅ Statistiques basiques
- ✅ Recommandations IA

### Version 1.1 (À venir)
- 🔜 Notifications push
- 🔜 Mode hors ligne
- 🔜 Export PDF des plans
- 🔜 Synchronisation Google Calendar

### Version 2.0 (Futur)
- 🌟 Gamification (badges, niveaux)
- 🌟 Classements amicaux
- 🌟 IA améliorée (GPT-4)
- 🌟 Application mobile native

## 🙏 Remerciements

Merci d'utiliser le Study Planner de DEFITECH !

Ce projet est développé avec ❤️ pour aider les étudiants à réussir.

---

**Version :** 1.0  
**Dernière mise à jour :** 28 Octobre 2025  
**Licence :** Propriétaire DEFITECH  
**Auteur :** Équipe DEFITECH