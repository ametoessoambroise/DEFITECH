# DefAI - Assistant IA pour Plateforme Universitaire

DefAI est un assistant intelligent basé sur Google Gemma 2B, fine-tuné spécifiquement pour les besoins d'une plateforme universitaire. Il peut analyser les comportements utilisateurs, assister le personnel, et s'intégrer parfaitement dans l'écosystème existant.

## 🎯 Objectifs

- **Analyse comportementale** : Comprendre les parcours utilisateurs et optimiser l'expérience
- **Assistance intelligente** : Aider les étudiants, enseignants et administrateurs
- **Débogage proactif** : Identifier et résoudre les problèmes rapidement
- **Intégration transparente** : S'intégrer dans les systèmes existants via API REST

## 📁 Structure du Projet

```
fineTuning_defAI/
├── config/                     # Fichiers de configuration
│   ├── training_config.yaml    # Configuration d'entraînement
│   └── model_config.yaml       # Configuration du modèle
├── data/                       # Données d'entraînement
│   ├── raw/                    # Données brutes extraites
│   ├── formatted/              # Données formatées pour le training
│   └── synthetic/              # Données synthétiques générées
├── scripts/                    # Scripts Python
│   ├── extract_db_data.py      # Extraction PostgreSQL
│   ├── track_routes.py         # Middleware Flask de tracking
│   ├── generate_dataset.py     # Génération du dataset
│   ├── train.py                # Fine-tuning Gemma 2B
│   └── evaluate.py             # Évaluation du modèle
├── model/                      # Modèles
│   ├── gemma_base/            # Gemma 2B de base
│   └── gemma_finetuned/       # DefAI fine-tuné
├── deployment/                 # Déploiement
│   ├── inference.py           # API d'inférence
│   └── routes_middleware.py   # Middleware d'intégration
├── tests/                      # Tests unitaires
└── README.md                   # Ce fichier
```

## 🚀 Installation et Configuration

### Prérequis

- Python 3.9+
- PostgreSQL (pour l'extraction de données)
- GPU NVIDIA (recommandé pour le fine-tuning)
- 16GB+ RAM (minimum)

### Installation des Dépendances

```bash
# Cloner le projet
git clone <https://github.com/Smiler00/fineTuning_defAI.git>
cd fineTuning_defAI

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### Configuration de l'Environnement

Créer un fichier `.env` à la racine :

```bash
# Configuration PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=university_db
DB_USER=postgres
DB_PASSWORD=your_password

# Configuration DefAI
DEFAI_URL=http://localhost:5000
DEFAI_TIMEOUT=30
DEFAI_ENABLED=true

# Configuration HuggingFace
HF_TOKEN=your_huggingface_token
```

## 📊 Étape 1 : Extraction des Données

Extrayez les données de votre base PostgreSQL existante :

```bash
cd scripts
python extract_db_data.py
```

Ce script :

- Se connecte à PostgreSQL
- Extrait les données des tables : users, teachers, students, courses, grades, user_routes_logs
- Sanitise les informations sensibles (emails, mots de passe, téléphones)
- Exporte en format JSON Lines dans `data/raw/`

## 🛣️ Étape 2 : Tracking des Routes

Intégrez le middleware Flask dans votre application existante :

```python
from track_routes import RouteTracker

app = Flask(__name__)
tracker = RouteTracker(app)

# Le middleware capturera automatiquement toutes les routes
```

Ou utilisez-le comme décorateur :

```python
@app.route('/dashboard')
@track_route()
def dashboard():
    return render_template('dashboard.html')
```

Le tracker enregistre :

- Route et méthode HTTP
- Informations utilisateur
- Durée de traitement
- Codes d'erreur
- Métadonnées contextuelles

## 🧠 Étape 3 : Génération du Dataset

Générez le dataset d'entraînement combinant données réelles et synthétiques :

```bash
cd scripts
python generate_dataset.py
```

Ce script :

- Charge les données brutes
- Génère des exemples synthétiques pour :
  - Assistance utilisateur
  - Analyse de routes
  - Résolution d'erreurs
  - Tâches administratives
- Crée les splits train/valid/test (80%/15%/5%)
- Sauvegarde en JSON Lines dans `data/formatted/`

## 🏋️ Étape 4 : Fine-Tuning du Modèle

Entraînez DefAI avec Gemma 2B et LoRA/QLoRA :

```bash
cd scripts
python train.py
```

Configuration via `config/training_config.yaml` :

- Modèle : Google Gemma 2B
- Technique : LoRA/QLoRA (quantification 4-bit)
- Hyperparamètres optimisés
- Monitoring automatique

**Hyperparamètres par défaut :**

- Learning rate : 2e-5
- Batch size : 2
- Époques : 3-5
- Max sequence length : 2048
- LoRA rank : 16

## 📈 Étape 5 : Évaluation

Évaluez les performances du modèle fine-tuné :

```bash
cd scripts
python evaluate.py
```

Métriques évaluées :

- BLEU, ROUGE-1/2/L
- Perplexité
- Tâches spécifiques DefAI
- Comparaison avec modèle de base

Résultats sauvegardés dans `evaluation_results/`

## 🚀 Étape 6 : Déploiement

### API d'Inférence

Démarrez l'API DefAI :

```bash
cd deployment
python inference.py --host 0.0.0.0 --port 5555
```

Endpoints disponibles :

- `POST /chat` - Chat avec l'IA
- `POST /analyze` - Analyse de situation
- `POST /assist` - Assistance utilisateur
- `POST /routes/suggest` - Suggestions de routes
- `POST /debug/error` - Aide au débogage
- `GET /health` - Vérification de l'état

### Intégration Middleware

Intégrez DefAI dans votre application existante :

```python
from routes_middleware import create_defai_app

# Créer l'application avec DefAI intégré
app = create_defai_app()

# Ou ajouter à une application existante
from routes_middleware import DefAIMiddleware
middleware = DefAIMiddleware(app)
```

## 📝 Utilisation

### Chat avec DefAI

```python
import requests

response = requests.post('http://localhost:5555/chat', json={
    'message': 'Comment un étudiant peut-il consulter ses notes ?'
})

print(response.json()['response'])
```

### Assistance Utilisateur

```python
response = requests.post('http://localhost:5000/assist', json={
    'query': 'Je ne peux pas accéder à mes cours',
    'user_role': 'student'
})
```

### Débogage d'Erreurs

```python
response = requests.post('http://localhost:5000/debug/error', json={
    'error_info': 'Erreur 500 lors de la soumission du formulaire'
})
```

## 🔧 Configuration Avancée

### Customisation du Dataset

Modifiez `scripts/generate_dataset.py` pour ajouter vos propres templates :

```python
# Ajouter de nouveaux templates
custom_templates = [
    {
        'instruction': 'Comment {action} dans {module} ?',
        'response': 'Pour {action} dans {module}, vous devez...',
        'variables': ['action', 'module']
    }
]
```

### Hyperparamètres

Ajustez `config/training_config.yaml` :

```yaml
training:
  learning_rate: 1e-5 # Plus conservateur
  batch_size: 4 # Plus grand batch
  num_epochs: 10 # Plus d'époques

lora:
  r: 32 # Rank plus élevé
  alpha: 64 # Alpha plus élevé
```

### Production

Configuration Docker pour la production :

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "deployment/inference.py"]
```

## 🧪 Tests

Exécutez les tests :

```bash
python -m pytest tests/ -v
```

Tests disponibles :

- Tests unitaires pour chaque script
- Tests d'intégration API
- Tests de performance modèle

## 📊 Monitoring

### Logs

Les logs sont configurés pour chaque composant :

- Niveau INFO par défaut
- Fichiers de log dans `logs/`
- Rotation automatique

### Métriques

Surveillez les performances avec :

- Temps de réponse API
- Utilisation GPU/CPU
- Qualité des réponses
- Taux d'erreur

## 🔒 Sécurité

### Protection des Données

- Sanitisation automatique des données sensibles
- Masquage des emails, mots de passe, téléphones
- Chiffrement en transit (HTTPS)

### Sécurité API

- CORS configuré
- Validation des entrées
- Rate limiting recommandé
- Authentification à implémenter

## 🚨 Dépannage

### Problèmes Communs

**GPU non reconnu :**

```bash
# Vérifier CUDA
nvidia-smi
torch.cuda.is_available()
```

**Mémoire insuffisante :**

- Réduire batch_size
- Activer gradient_checkpointing
- Utiliser quantification 4-bit

**Modèle ne se charge pas :**

- Vérifier les chemins dans les configs
- Confirmer les permissions fichiers
- Redémarrer le service

### Support

Pour obtenir de l'aide :

1. Consulter les logs dans `logs/`
2. Vérifier la configuration `.env`
3. Tester avec le dataset minimal
4. Créer une issue sur GitHub

## 📈 Performance

### Benchmarks

Sur GPU RTX 3080 :

- Extraction données : ~2 minutes
- Génération dataset : ~5 minutes
- Fine-tuning : ~2 heures
- Inférence : ~100ms par requête

### Optimisations

- Utiliser CUDA pour le fine-tuning
- Quantification 4-bit pour réduire mémoire
- Batch size optimal selon GPU
- Cache des réponses fréquentes

## 🔄 Mises à Jour

### Versionning

- Tags Git pour chaque version
- Changelog détaillé
- Tests de régression
- Migration des configs

### Améliorations Futures

- Support multi-langues
- Interface web admin
- Dashboard analytics
- Intégration avec plus de systèmes

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour les détails.

## 🤝 Contribution

Les contributions sont bienvenues !

1. Fork le projet
2. Créer une branche feature
3. Faire les modifications
4. Ajouter des tests
5. Soumettre une PR

## 📞 Contact

Pour toute question ou suggestion :

- Créer une issue sur GitHub
- Contacter l'équipe de développement
- Consulter la documentation technique

---

**DefAI** - L'assistant intelligent qui transforme votre plateforme universitaire 🚀
