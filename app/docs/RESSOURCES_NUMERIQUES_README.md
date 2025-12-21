# Ressources Numériques - DEFITECH

## Description

La fonctionnalité "Ressources Numériques" permet aux enseignants de partager des documents pédagogiques (livres PDF, cours, TD, TP, examens, etc.) avec les étudiants de leur filière.

## Fonctionnalités

### Pour les Enseignants
- ✅ **Upload de ressources** : Interface simple pour uploader des fichiers
- ✅ **Gestion des types** : Cours, TD, TP, examens, livres, etc.
- ✅ **Organisation automatique** : Création automatique de dossiers par type
- ✅ **Gestion des permissions** : Contrôle d'accès par filière et année
- ✅ **Mes ressources** : Page personnelle pour gérer ses uploads

### Pour les Étudiants
- ✅ **Consultation filtrée** : Accès uniquement aux ressources de leur filière
- ✅ **Recherche avancée** : Recherche par titre, description, nom de fichier
- ✅ **Filtres multiples** : Par filière, année, type, matière
- ✅ **Téléchargement sécurisé** : Téléchargement direct des fichiers

### Pour les Administrateurs
- ✅ **Vue globale** : Accès à toutes les ressources du système
- ✅ **Statistiques** : Nombre de ressources par type, format, etc.

## Structure des fichiers

### Modèles
- `models/resource.py` : Modèle SQLAlchemy pour les ressources

### Routes
- `resources.py` : Blueprint avec toutes les routes de gestion

### Templates
- `templates/resources/index.html` : Page principale d'affichage
- `templates/resources/upload.html` : Formulaire d'upload
- `templates/resources/my_resources.html` : Gestion des ressources perso

## Installation et Configuration

### 1. Migration de la base de données
```bash
python create_resources_table.py
```

### 2. Extensions supportées
- Documents : PDF, DOC, DOCX, TXT
- Présentations : PPT, PPTX
- Tableurs : XLS, XLSX
- Archives : ZIP, RAR, 7Z
- Images : JPG, JPEG, PNG
- Taille maximale : 50 MB

### 3. Dossiers de stockage
Le système crée automatiquement :
```
static/uploads/resources/
├── cours/
├── livre/
├── td/
├── tp/
├── examen/
├── corrige/
├── support/
├── documentation/
├── autre/
└── temp/
```

## Utilisation

### Accès aux ressources
1. **Étudiants** : Menu → Ressources (accès automatique à leur filière)
2. **Enseignants** : Dashboard → "Ressources numériques"
3. **Administrateurs** : Accès à toutes les ressources

### Upload d'une ressource
1. Se connecter en tant qu'enseignant
2. Aller dans "Ressources numériques"
3. Cliquer sur "Ajouter une ressource"
4. Remplir le formulaire (titre, description, type, filière, année)
5. Sélectionner le fichier
6. Valider l'upload

### Recherche et filtres
- **Barre de recherche** : Recherche en temps réel
- **Filtres** : Filière, année, type de ressource, matière
- **Tri** : Par date d'upload (plus récent d'abord)

## Sécurité

### Permissions
- **Upload** : Enseignants uniquement
- **Consultation** : Étudiants (filière/année), Enseignants (leurs filières), Admins (tout)
- **Suppression** : Auteur de la ressource ou administrateur

### Validation
- Extension de fichier autorisée
- Taille de fichier (max 50MB)
- Type MIME vérifié
- Nom de fichier sécurisé

## API

### Routes principales
- `GET /resources/` : Liste des ressources avec filtres
- `GET /resources/upload` : Formulaire d'upload
- `POST /resources/upload` : Traitement de l'upload
- `GET /resources/download/<id>` : Téléchargement d'une ressource
- `POST /resources/delete/<id>` : Suppression d'une ressource
- `GET /resources/my-resources` : Ressources de l'utilisateur

### Paramètres de recherche
- `search` : Texte de recherche
- `filiere` : Filtrage par filière
- `annee` : Filtrage par année
- `type_ressource` : Filtrage par type
- `matiere_id` : Filtrage par matière

## Intégration avec les emails

Les ressources sont automatiquement intégrées dans le système de notifications par email. Quand un enseignant upload une nouvelle ressource, les étudiants concernés peuvent être notifiés via le système de notifications globales.

## Développement

### Ajout de nouveaux types de ressources
1. Ajouter le type dans `RESOURCE_TYPES` dans `resources.py`
2. Créer le dossier correspondant dans `create_resource_folders()`
3. Mettre à jour les templates si nécessaire

### Personnalisation des icônes
Les icônes sont définies dans la propriété `icone_type` du modèle `Resource`. Utilise Font Awesome.

### Extensions des permissions
Le système de permissions peut être étendu dans les méthodes :
- `get_resources_for_user()` : Récupération selon le rôle
- Routes individuelles : Vérifications spécifiques

## Maintenance

### Nettoyage des fichiers orphelins
```python
# Script à exécuter périodiquement
from models.resource import Resource
import os

# Supprimer les fichiers dont la base de données n'existe plus
for resource in Resource.query.all():
    if not os.path.exists(resource.chemin_fichier):
        print(f"Fichier manquant: {resource.chemin_fichier}")
        # Optionnel: db.session.delete(resource)
```

### Statistiques
```python
# Récupération des statistiques
from models.resource import Resource

total = Resource.query.count()
par_type = Resource.query.group_by(Resource.type_ressource).count()
par_extension = Resource.query.group_by(Resource.type_fichier).count()
```

## Support

En cas de problème :
1. Vérifier les logs de l'application
2. Contrôler les permissions des dossiers `static/uploads/`
3. Vérifier la configuration de la base de données
4. Tester l'upload avec des fichiers de petite taille
