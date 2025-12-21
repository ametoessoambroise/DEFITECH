# defAI - Assistant IA DEFITECH (Version Améliorée)

## 🎯 Vue d'ensemble

Interface de chat IA moderne inspirée de Claude.ai, offrant une expérience utilisateur fluide et intuitive avec support des réponses longues dans une sidebar dédiée.

## ✨ Fonctionnalités implémentées

### 🎨 Interface utilisateur (Style Claude.ai)

- **Layout épuré** : Design minimaliste avec sidebar de conversations cachée par défaut
- **Welcome screen** : Écran d'accueil centré avec logo et message de bienvenue
- **Container de chat centré** : Messages dans un conteneur max-width 4xl pour une meilleure lisibilité
- **Thème clair/sombre** : Basculement fluide entre les deux modes
- **Animations fluides** : Transitions et animations subtiles pour une UX moderne

### 💬 Système de messages

- **Bulles utilisateur** : Alignées à droite, fond bleu (#3b82f6)
- **Bulles IA** : Alignées à gauche, fond gris clair/sombre selon le thème
- **Largeur adaptative** : Les messages prennent toute la largeur disponible (max-width 85% pour user, 100% pour IA)
- **Rendu Markdown** : Support complet avec highlight.js pour la coloration syntaxique
- **Bouton copier** : Sur chaque message IA pour faciliter la copie

### 📄 Sidebar automatique pour réponses longues

#### Déclenchement automatique

- **Seuil** : 1000 caractères
- **Ouverture automatique** : La sidebar s'ouvre dès que la réponse dépasse le seuil
- **Placeholder dans le chat** : Message avec icône indiquant que la réponse est dans le panneau latéral

#### Fonctionnalités de la sidebar

- **Titre** : "Réponse détaillée" avec icône
- **Contenu scrollable** : Rendu Markdown complet
- **Boutons d'action** :
  - 📋 **Copier** : Copie le texte complet dans le presse-papiers
  - 📄 **PDF** : Télécharge la réponse en format PDF
  - 📝 **TXT** : Télécharge la réponse en format texte
  - ❌ **Fermer** : Ferme la sidebar (ne se rouvre pas automatiquement)

#### Comportement

- **Persiste** : Reste ouverte même si l'utilisateur envoie d'autres messages
- **Fermeture manuelle** : Uniquement via le bouton "Fermer"
- **Réouverture** : Clic sur le placeholder dans le chat

### 📱 Responsive mobile parfait

- **< 768px** : Sidebars en overlay plein écran avec fond semi-transparent
- **Sidebar conversations** : Overlay z-index 30
- **Sidebar réponses** : Overlay z-index 40 (au-dessus)
- **Pas de débordements** : Tout le contenu s'adapte parfaitement
- **Input sticky** : Zone de saisie toujours accessible en bas

### 🗂️ Gestion des conversations

- **Liste des conversations** : Sidebar gauche avec historique
- **Création** : Nouvelle conversation via bouton header
- **Chargement** : Clic sur une conversation pour la recharger
- **Suppression** : Bouton de suppression au hover (icône poubelle)
- **Titre automatique** : Basé sur le premier message

### ⚙️ Paramètres et configuration

- **Modal paramètres** : Accès via icône engrenage dans le header
- **Sélection du modèle** : Gemini 2.0 Flash, GPT-4, Claude 3
- **Température** : Slider 0-1 pour contrôler la créativité
- **Export PDF/TXT** : Export de toute la conversation
- **Vider conversation** : Réinitialisation complète

### 🎨 Génération d'images

- **Modal dédiée** : Interface pour générer des images via IA
- **Affichage inline** : Images générées affichées dans le chat
- **Quota visuel** : Indicateur de quota d'images disponibles

### 📎 Pièces jointes

- **Bouton paperclip** : Upload de fichiers (images, PDF, documents)
- **Prévisualisation** : Affichage du nom du fichier joint

### 🎯 Actions supplémentaires

- **Bouton retour** : Navigation vers la page précédente
- **Bouton nouveau** : Création rapide d'une nouvelle conversation
- **Auto-resize textarea** : Zone de saisie qui s'agrandit automatiquement (max 200px)
- **Indicateur de frappe** : 3 dots animés pendant la génération

## 🏗️ Structure HTML

```
<body>
  <header> (fixed top)
    - Bouton menu conversations
    - Logo + titre
    - Boutons actions (retour, nouveau, paramètres)
  </header>

  <main> (flex container)
    <!-- Sidebar gauche (conversations) -->
    <aside id="conversationsSidebar" class="sidebar-left">
      - Liste des conversations
      - Scroll vertical
    </aside>

    <!-- Zone de chat centrale -->
    <div id="chatContainer">
      <!-- Messages -->
      <div id="messagesContainer">
        - Welcome screen OU liste des messages
      </div>

      <!-- Input fixe en bas -->
      <div class="input-area">
        - Textarea auto-resize
        - Boutons (attachement, image)
        - Bouton envoyer
      </div>
    </div>

    <!-- Sidebar droite (réponses longues) -->
    <aside id="responseSidebar" class="sidebar-right">
      - Contenu markdown
      - Boutons d'action
    </aside>
  </main>

  <!-- Overlay mobile -->
  <div id="overlay"></div>

  <!-- Modals -->
  <div id="settingsModal">...</div>
  <div id="imageModal">...</div>
</body>
```

## 🔌 Endpoints Backend (Flask)

### Chat

- `POST /ai/chat` : Envoi d'un message
  - Body: `{message, conversation_id, model, temperature}`
  - Response: `{response, conversation_id}`

### Conversations

- `GET /ai/conversations` : Liste toutes les conversations
- `GET /ai/conversations/{id}` : Charge une conversation spécifique
- `DELETE /ai/conversations/{id}` : Supprime une conversation

### Génération d'images

- `POST /ai/generate-image` : Génère une image
  - Body: `{prompt}`
  - Response: `{image_url, quota_remaining}`

### Pièces jointes

- Upload vers `/static/uploads/ai_attachments/{conversation_id}/{filename}`

## 🎨 Design et couleurs

### Variables CSS

```css
--defai-blue: #3b82f6;
--defai-blue-dark: #1d4ed8;
--user-bubble-bg: #3b82f6 (light) / #1d4ed8 (dark);
--ai-bubble-bg: #f3f4f6 (light) / #1e293b (dark);
```

### Breakpoints responsive

- **Desktop** : > 1024px (sidebar 400px)
- **Tablet** : 768px - 1024px (sidebar 350px)
- **Mobile** : < 768px (sidebar plein écran overlay)

## 📦 Dépendances CDN

- **Tailwind CSS** : Styling utility-first
- **Font Awesome 6.4.0** : Icônes
- **Marked.js** : Parsing Markdown
- **DOMPurify 3.0.6** : Sanitization XSS
- **Highlight.js 11.9.0** : Coloration syntaxique
- **jsPDF 2.5.1** : Export PDF
- **Google Fonts (Inter)** : Typographie moderne

## ⚡ Fonctions JavaScript principales

### Gestion des sidebars

- `toggleConversationsSidebar()` : Ouvre/ferme la sidebar conversations
- `openResponseSidebar(content)` : Ouvre la sidebar avec une réponse longue
- `closeResponseSidebar()` : Ferme la sidebar réponses
- `closeAllSidebars()` : Ferme toutes les sidebars

### Gestion des messages

- `sendMessage()` : Envoie un message à l'API
- `addMessage(role, content)` : Ajoute un message au chat
- `addLongResponsePlaceholder()` : Ajoute le placeholder pour réponse longue
- `addTypingIndicator()` : Affiche l'indicateur de frappe

### Gestion des conversations

- `loadConversations()` : Charge la liste des conversations
- `loadConversation(id)` : Charge une conversation spécifique
- `createNewConversation()` : Crée une nouvelle conversation
- `deleteConversation(id)` : Supprime une conversation

### Actions sur les réponses

- `copyResponseContent()` : Copie la réponse longue
- `downloadResponsePDF()` : Télécharge en PDF
- `downloadResponseTXT()` : Télécharge en TXT

### Utilitaires

- `safeMarkdown(text)` : Parse et sanitize le Markdown
- `autoResizeTextarea()` : Redimensionne automatiquement le textarea
- `scrollToBottom()` : Scroll vers le bas du chat

## 🚀 Améliorations implémentées vs. version originale

### ✅ Supprimé

- ❌ Section statistiques (messages, caractères, mots)
- ❌ 4 cartes de fonctionnalités sur le welcome screen
- ❌ Sidebar actions toujours visible
- ❌ Largeur limitée des messages (80%)

### ✅ Ajouté

- ✅ Sidebar automatique pour réponses > 1000 caractères
- ✅ Placeholder cliquable dans le chat
- ✅ Boutons d'export dans la sidebar réponse
- ✅ Welcome screen minimaliste et centré
- ✅ Layout inspiré de Claude.ai
- ✅ Sidebars cachées par défaut
- ✅ Messages pleine largeur (max-width adaptatif)
- ✅ Animations et transitions fluides
- ✅ Responsive mobile parfait sans débordements

## 🔧 Configuration

### Seuil de réponse longue

```javascript
const LONG_RESPONSE_THRESHOLD = 1000; // Modifiable selon vos besoins
```

### Modèle par défaut

```javascript
let currentModel = "gemini-2.0-flash-exp";
let currentTemperature = 0.7;
```

## 📝 Notes de développement

### Compatibilité backend

- Tous les endpoints Flask existants sont conservés
- Les variables Jinja2 (`{{ url_for(...) }}`, `{{ csrf_token() }}`) sont maintenues
- La structure de données des messages est identique

### Thème persistant

- Le thème est sauvegardé dans `localStorage`
- Récupération automatique au chargement de la page

### Gestion d'état

- `currentConversationId` : ID de la conversation active
- `currentLongResponse` : Contenu de la réponse longue actuelle
- `isTyping` : Indicateur de génération en cours

## 🎯 Prochaines étapes recommandées

1. **Recherche dans les conversations** : Ajouter une barre de recherche dans la sidebar
2. **Tags/catégories** : Organiser les conversations par thèmes
3. **Raccourcis clavier** : Navigation rapide (Ctrl+N, Ctrl+K, etc.)
4. **Partage de conversations** : Export en lien partageable
5. **Voice input** : Reconnaissance vocale pour la saisie
6. **Multi-langue** : Support de plusieurs langues d'interface
7. **Markdown editor** : Mode d'édition avancé avec prévisualisation
8. **Favoris** : Marquer des messages importants
9. **Mode focus** : Cache tout sauf le chat
10. **Historique illimité** : Pagination et chargement lazy des anciennes conversations

## 📄 Licence

Propriété de DEFITECH - Tous droits réservés

## 🤝 Support

Pour toute question ou amélioration, contactez l'équipe DEFITECH.

---

**Version** : 2.0 (Refonte complète)  
**Date** : 2025  
**Auteur** : Assistant IA pour DEFITECH
v