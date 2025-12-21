# Documentation du Système DefAI Internal Request

## Vue d'ensemble

Le système DefAI Internal Request System est une infrastructure sécurisée qui permet à l'assistant IA DefAI d'effectuer des requêtes internes vers l'application Flask de manière contrôlée et sécurisée.

## Architecture

Le système se compose de 4 composants principaux :

### 1. **defai_middleware.py** - Middleware Flask
- **Rôle** : Intercepte et valide toutes les requêtes venant de DefAI
- **Fonctionnalités** :
  - Authentification par signature HMAC avec timestamp
  - Validation anti-replay (cache des requêtes)
  - Vérification des endpoints autorisés (liste blanche)
  - Logging des accès et erreurs

### 2. **defai_permissions.py** - Gestion des autorisations
- **Rôle** : Définit les permissions par rôle et les endpoints accessibles
- **Fonctionnalités** :
  - Configuration des endpoints autorisés par catégorie (ai, role_data, api)
  - Mapping des rôles utilisateurs vers les rôles DefAI
  - Actions spéciales avec validation supplémentaire
  - Configuration du logging et des timeouts

### 3. **defai_client.py** - Client interne DefAI
- **Rôle** : Permet à DefAI d'envoyer des requêtes authentifiées
- **Fonctionnalités** :
  - Génération automatique des signatures HMAC
  - Retry automatique en cas d'échec
  - Helper methods pour les opérations courantes
  - Gestion des erreurs centralisée

### 4. **Intégration dans ai_orchestrator.py**
- **Rôle** : Utilise le nouveau système pour les requêtes intelligentes
- **Fonctionnalités** :
  - Mapping des requêtes vers les endpoints DefAI
  - Fallback vers les méthodes locales existantes
  - Logging des performances

## Configuration

### Variables d'environnement

```bash
# Clé secrète pour les signatures DefAI (obligatoire)
DEFAI_SECRET_KEY=votre-cle-secrete-tres-longue-et-complexe

# Activer/désactiver le middleware DefAI
DEFAI_ENABLED=true
```

### Configuration dans app.py

Le middleware est automatiquement initialisé si `DEFAI_ENABLED=true` :

```python
# Configuration DefAI
app.config["DEFAI_SECRET_KEY"] = os.getenv("DEFAI_SECRET_KEY", "defai-secret-key-change-in-production")
app.config["DEFAI_ENABLED"] = os.getenv("DEFAI_ENABLED", "true").lower() in ("true", "1", "t")
app.config["DEFAI_ACCESS_KEY"] = os.getenv("DEFAI_ACCESS_KEY", "defai-internal-key")
app.config["DEFAI_ALLOWED_ENDPOINTS"] = DEFAI_ALLOWED_ENDPOINTS

# Initialisation automatique
if app.config.get("DEFAI_ENABLED", True):
    from defai_middleware import DefAIMiddleware
    defai_middleware = DefAIMiddleware(app)
```

## Utilisation

### Pour DefAI (requêtes sortantes)

```python
from defai_client import get_defai_client, DefAIHelper

# Utilisation du client basique (avec rôle explicite)
client = get_defai_client()
result = client.get_json(
    "/api/role-data/etudiant/grades?student_id=123",
    user_role="etudiant",
    user_id=123
)

# Utilisation des helpers
helper = DefAIHelper()
conversations = helper.get_user_conversations(user_id=123)
grades = helper.get_student_grades(student_id=123)
```

### Authentification des requêtes

Le client génère automatiquement les headers nécessaires :

```python
# Headers générés automatiquement
{
    'X-DefAI-Key': 'defai-internal',
    'X-DefAI-Timestamp': '1640995200',
    'X-DefAI-Signature': 'hash_hmac_sha256...',
    'X-DefAI-User-Role': 'etudiant',
    'X-DefAI-User-Id': '123',
    'X-DefAI-Request-Id': 'uuid...',
    'Content-Type': 'application/json'
}
```

### Pour l'application Flask (requêtes entrantes)

Les endpoints sont automatiquement protégés par le middleware. Aucune modification n'est nécessaire sur les routes existantes.

## Sécurité

### 1. **Authentification forte**
- Signatures HMAC SHA-256 avec clé secrète
- Timestamp pour prévenir les attaques replay
- Validation de la fraîcheur des requêtes (5 minutes max)

### 2. **Liste blanche stricte**
- Seuls les endpoints explicitement autorisés sont accessibles
- Permissions granulaires par rôle
- Actions spéciales avec validation supplémentaire

### 3. **Anti-replay**
- Cache des signatures utilisées
- TTL de 5 minutes pour le cache
- Nettoyage automatique des entrées expirées

### 4. **Logging complet**
- Tous les accès DefAI sont loggés
- Erreurs de sécurité séparées
- Audit trail complet
- Fichiers disponibles dans `logs/defai_access.log`, `logs/defai_security.log`, `logs/defai_errors.log`

## Gestion des permissions

1. **Ajouter une route**
   - Ouvrir `defai_permissions.py`
   - Ajouter l'entrée `"METHOD /path"` dans la catégorie appropriée (`ai`, `role_data`, `api`)
   - Optionnel : utiliser `get_all_allowed_endpoints()` pour vérifier la configuration.

2. **Appeler une route**
   - Utiliser `DefAIClient` en passant `user_role` (français : `etudiant`, `enseignant`, `admin`)
   - Fournir `user_id` lorsque la route agit au nom d'un utilisateur.
   - Le middleware vérifiera automatiquement la signature et la liste blanche.

3. **Vérifier les accès**
   - Consulter `logs/defai_access.log` pour la trace complète
   - Les accès refusés apparaissent dans `logs/defai_security.log`
   - Les erreurs applicatives sont loggées dans `logs/defai_errors.log`

## Endpoints autorisés

### Assistant IA (/ai)
- `GET /ai/conversations`
- `POST /ai/conversations`
- `GET /ai/conversations/<id>/messages`
- `POST /ai/chat`
- `POST /ai/upload`
- `GET /ai/dataset/stats`

### Données par rôle (/api/role-data)

#### Étudiant
- `GET /api/role-data/etudiant/grades`
- `GET /api/role-data/etudiant/schedule`
- `GET /api/role-data/etudiant/assignments`
- `GET /api/role-data/etudiant/notifications`

#### Enseignant
- `GET /api/role-data/enseignant/classes`
- `GET /api/role-data/enseignant/subjects`
- `GET /api/role-data/enseignant/class-stats/<id>`

#### Admin
- `GET /api/role-data/admin/platform-stats`
- `GET /api/role-data/admin/system-health`
- `GET /api/role-data/admin/users`
- `POST /api/role-data/admin/notify`

### API générale (/api)
- Accès limité selon le rôle utilisateur
- Endpoints de lecture/écriture contrôlés
- Actions spéciales réservées aux admins

## Dépannage

### Erreurs communes

#### 1. "Authentication failed"
- Vérifier que `DEFAI_SECRET_KEY` est configurée
- S'assurer que les horloges sont synchronisées
- Vérifier le format des headers

#### 2. "Endpoint not allowed"
- Vérifier que l'endpoint est dans la liste blanche
- Confirmer que le rôle utilisateur a les permissions
- Vérifier la méthode HTTP (GET/POST/PUT/DELETE)

#### 3. "Replay attack detected"
- Attendre 5 minutes avant de réessayer la même requête
- Vérifier que les timestamps sont uniques
- Nettoyer le cache si nécessaire

### Debug mode

Pour activer le debug DefAI :

```python
import logging
logging.getLogger('defai_middleware').setLevel(logging.DEBUG)
logging.getLogger('defai_client').setLevel(logging.DEBUG)
```

## Performance

### Optimisations
- Cache des permissions en mémoire
- Timeout configurable pour les requêtes
- Retry automatique avec backoff exponentiel
- Connection pooling via requests.Session

### Monitoring
- Temps de réponse des requêtes DefAI
- Taux d'erreur par endpoint
- Volume de requêtes par rôle
- Alertes sur les tentatives d'accès non autorisées

## Maintenance

### Mises à jour
1. Ajouter de nouveaux endpoints dans `defai_permissions.py`
2. Mettre à jour les mappings dans `ai_orchestrator.py`
3. Tester avec le client DefAI
4. Monitorer les logs pour détecter les problèmes

### Sécurité
1. Rotation régulière des clés secrètes
2. Surveillance des logs de sécurité
3. Audit des permissions par rôle
4. Tests de pénétration périodiques

## Exemples d'utilisation

### Créer une conversation IA
```python
helper = DefAIHelper()
conversation = helper.create_conversation(
    user_id=123,
    user_role="etudiant",
    title="Aide en mathématiques"
)
```

### Récupérer les notes d'un étudiant
```python
grades = helper.get_student_grades(student_id=123)
if grades.get("success"):
    notes = grades["grades"]
    # Traitement des notes
```

### Notifier des utilisateurs
```python
result = helper.notify_users(
    message="Nouveau devoir disponible",
    target_roles=["etudiant"],
    target_users=[123, 456]
)
```

## Conclusion

Le système DefAI Internal Request System offre une infrastructure sécurisée et performante pour les interactions entre l'assistant IA et l'application. Il garantit la sécurité tout en maintenant une flexibilité suffisante pour les évolutions futures.

Pour toute question ou problème technique, consultez les logs dans `logs/defai_*.log` ou contactez l'équipe de développement.
