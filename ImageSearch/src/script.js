// Configuration de l'application
const CONFIG = {
  BACKEND_URL: 'http://localhost:8000', // URL du backend FastAPI
  DEFAULT_IMAGES_PER_PAGE: 12,
  // Configuration Cloudinary pour l'analyse d'images
  CLOUDINARY: {
    CLOUD_NAME: 'doqjyyf8w',
    UPLOAD_PRESET: 'ml_default',
    UPLOAD_URL: 'https://api.cloudinary.com/v1_1/doqjyyf8w/image/upload',
    SIMULATION_MODE: true // Mode simulation par défaut
  }
};

// Éléments du DOM
const elements = {
  // Recherche
  searchInput: document.getElementById('searchImageInput'),
  searchButton: document.getElementById('searchImageButton'),
  searchType: document.getElementById('searchType'),
  colorFilter: document.getElementById('colorFilter'),
  suggestions: document.querySelectorAll('.suggestion-tag'),
  imageContainer: document.getElementById('imageContainer'),
  loadMoreBtn: document.getElementById('loadMoreBtn'),
  searchLoader: document.getElementById('searchLoader'),

  // Génération
  aiPrompt: document.getElementById('aiPrompt'),
  aiStyle: document.getElementById('aiStyle'),
  generateImageBtn: document.getElementById('generateImageBtn'),
  generatedImages: document.getElementById('generatedImages'),
  generateLoader: document.getElementById('generateLoader'),

  // Modal
  modal: document.getElementById('imageModal'),
  modalImage: document.getElementById('modalImage'),
  modalTitle: document.getElementById('modalTitle'),
  modalDescription: document.getElementById('modalDescription'),
  closeModal: document.querySelector('.close-modal'),
  downloadBtn: document.getElementById('downloadBtn'),
  shareBtn: document.getElementById('shareBtn'),
  generateSimilarBtn: document.getElementById('generateSimilarBtn'),

  // Analyse d'image
  dropZone: document.getElementById('dropZone'),
  browseBtn: document.getElementById('browseBtn'),
  fileInput: document.getElementById('fileInput'),
  analyzeBtn: document.getElementById('analyzeBtn'),
  previewImage: document.getElementById('previewImage'),
  analysisResults: document.getElementById('analysisResults'),
  analysisTags: document.getElementById('analysisTags')
};

// État de l'application
const state = {
  currentPage: 1,
  currentSearchQuery: '',
  currentImage: null,
  fileToAnalyze: null
};

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  setupImageAnalysis();
  setupTabNavigation();
  fetchPopularImages();
});

// Configuration de la navigation par onglets
function setupTabNavigation() {
  const tabButtons = document.querySelectorAll('.tab-btn:not(#dark)');
  const tabContents = document.querySelectorAll('.tab-content');

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabName = button.getAttribute('data-tab');

      // Retirer la classe active de tous les boutons et contenus
      tabButtons.forEach(btn => btn.classList.remove('active'));
      tabContents.forEach(content => content.classList.remove('active'));

      // Ajouter la classe active au bouton et contenu sélectionnés
      button.classList.add('active');
      const activeContent = document.getElementById(`${tabName}-tab`);
      if (activeContent) {
        activeContent.classList.add('active');
      }
    });
  });
}

// Configuration des écouteurs d'événements
function setupEventListeners() {
  // Recherche d'images
  if (elements.searchButton) {
    elements.searchButton.addEventListener('click', handleSearch);
  }

  if (elements.searchInput) {
    elements.searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleSearch();
    });
  }

  // Suggestions de recherche
  elements.suggestions.forEach(suggestion => {
    suggestion.addEventListener('click', () => {
      elements.searchInput.value = suggestion.textContent;
      handleSearch();
    });
  });

  // Filtres
  if (elements.searchType) {
    elements.searchType.addEventListener('change', handleSearch);
  }
  if (elements.colorFilter) {
    elements.colorFilter.addEventListener('change', handleSearch);
  }

  // Bouton "Afficher plus"
  if (elements.loadMoreBtn) {
    elements.loadMoreBtn.addEventListener('click', loadMoreImages);
  }

  // Génération d'images
  if (elements.generateImageBtn) {
    elements.generateImageBtn.addEventListener('click', handleGenerateImage);
  }

  // Modal
  if (elements.closeModal) {
    elements.closeModal.addEventListener('click', closeModal);
  }
  if (elements.downloadBtn) {
    elements.downloadBtn.addEventListener('click', downloadImage);
  }
  if (elements.shareBtn) {
    elements.shareBtn.addEventListener('click', shareImage);
  }
  if (elements.generateSimilarBtn) {
    elements.generateSimilarBtn.addEventListener('click', generateSimilarImage);
  }

  // Fermer la modal en cliquant en dehors
  window.addEventListener('click', (e) => {
    if (e.target === elements.modal) {
      closeModal();
    }
  });
}

// Configuration de l'analyse d'image
function setupImageAnalysis() {
  if (!elements.browseBtn || !elements.fileInput || !elements.dropZone || !elements.analyzeBtn) {
    console.warn('Certains éléments d\'analyse d\'image sont manquants');
    return;
  }

  // Clic sur le bouton Parcourir
  elements.browseBtn.addEventListener('click', (e) => {
    e.preventDefault();
    elements.fileInput.click();
  });

  // Sélection de fichier
  elements.fileInput.addEventListener('change', handleFileSelect);

  // Glisser-déposer
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    elements.dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    }, false);
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    elements.dropZone.addEventListener(eventName, () => {
      elements.dropZone.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    elements.dropZone.addEventListener(eventName, () => {
      elements.dropZone.classList.remove('dragover');
    }, false);
  });

  elements.dropZone.addEventListener('drop', handleDrop, false);

  // Bouton d'analyse
  elements.analyzeBtn.addEventListener('click', analyzeImage);
  elements.analyzeBtn.disabled = true;
}

// Gérer la sélection de fichier
function handleFileSelect(e) {
  const files = e.target.files;
  if (files && files.length > 0) {
    processImage(files[0]);
  }
  elements.fileInput.value = '';
}

// Gérer le dépôt de fichier
function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  if (files && files.length > 0) {
    processImage(files[0]);
  }
}

// Traiter l'image sélectionnée
function processImage(file) {
  if (!file) {
    showToast('Aucun fichier sélectionné', 'error');
    return;
  }

  if (!file.type.match('image.*')) {
    showToast('Veuillez sélectionner une image valide (JPG, PNG, etc.)', 'error');
    return;
  }

  const maxSize = 5 * 1024 * 1024; // 5MB
  if (file.size > maxSize) {
    showToast('L\'image ne doit pas dépasser 5 Mo', 'error');
    return;
  }

  const reader = new FileReader();

  reader.onload = function (e) {
    elements.previewImage.src = e.target.result;
    elements.previewImage.style.display = 'block';
    elements.analyzeBtn.disabled = false;
    state.fileToAnalyze = file;
    elements.analysisResults.style.display = 'none';

    setTimeout(() => {
      elements.previewImage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  };

  reader.onerror = function () {
    showToast('Erreur lors de la lecture du fichier', 'error');
  };

  reader.readAsDataURL(file);
}

// Analyser l'image
async function analyzeImage() {
  if (!state.fileToAnalyze) {
    showToast('Veuillez sélectionner une image à analyser', 'error');
    return;
  }

  try {
    elements.analyzeBtn.disabled = true;
    elements.analyzeBtn.classList.add('analyzing');
    elements.analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyse en cours...';

    // Simulation de l'analyse (mode démo)
    const analysisResult = await simulateImageAnalysis(URL.createObjectURL(state.fileToAnalyze));
    displayAnalysisResults(analysisResult);

  } catch (error) {
    console.error('Erreur d\'analyse:', error);
    showToast(`Erreur: ${error.message}`, 'error');
  } finally {
    elements.analyzeBtn.disabled = false;
    elements.analyzeBtn.classList.remove('analyzing');
    elements.analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyser l\'image';
  }
}

// Simuler l'analyse d'image
async function simulateImageAnalysis(imageUrl) {
  await new Promise(resolve => setTimeout(resolve, 1500));

  const categories = {
    nature: ['forêt', 'montagne', 'rivière', 'océan', 'plage', 'cascade', 'lac', 'désert', 'champ', 'fleur', 'arbre', 'ciel'],
    urbain: ['ville', 'bâtiment', 'rue', 'pont', 'architecture', 'gratte-ciel', 'métro', 'parc', 'fontaine', 'monument'],
    personnes: ['portrait', 'sourire', 'groupe', 'enfant', 'famille', 'couple', 'ami', 'voyage', 'aventure', 'sport'],
    animaux: ['chat', 'chien', 'oiseau', 'paysage', 'sauvage', 'nature', 'mignon', 'compagnon', 'faune'],
    nourriture: ['repas', 'restaurant', 'dessert', 'boisson', 'fruit', 'légume', 'cuisine', 'recette', 'gourmandise']
  };

  const categoryKeys = Object.keys(categories);
  const randomCategory = categoryKeys[Math.floor(Math.random() * categoryKeys.length)];
  const baseTags = [...categories[randomCategory]];

  const selectedTags = [];
  const numTags = 3 + Math.floor(Math.random() * 4);

  while (selectedTags.length < numTags && baseTags.length > 0) {
    const randomIndex = Math.floor(Math.random() * baseTags.length);
    selectedTags.push(baseTags.splice(randomIndex, 1)[0]);
  }

  return {
    tags: selectedTags,
    metadata: {
      width: 800 + Math.floor(Math.random() * 2000),
      height: 600 + Math.floor(Math.random() * 1500),
      format: ['JPEG', 'PNG', 'WEBP'][Math.floor(Math.random() * 3)],
      category: randomCategory,
      confidence: (70 + Math.floor(Math.random() * 30)) + '%'
    }
  };
}

// Afficher les résultats de l'analyse
function displayAnalysisResults(analysis) {
  elements.analysisResults.style.display = 'block';
  elements.analysisTags.innerHTML = '';

  analysis.tags.forEach(tag => {
    const tagElement = document.createElement('span');
    tagElement.className = 'tag';
    tagElement.textContent = tag;
    elements.analysisTags.appendChild(tagElement);
  });

  setTimeout(() => {
    elements.analysisResults.classList.add('visible');
    elements.analysisResults.scrollIntoView({ behavior: 'smooth' });
  }, 100);
}

// Charger des images populaires au démarrage
async function fetchPopularImages() {
  try {
    showLoader('searchLoader');

    // Appel au backend
    const response = await fetch(`${CONFIG.BACKEND_URL}/api/search?query=popular&per_page=${CONFIG.DEFAULT_IMAGES_PER_PAGE}`);

    if (!response.ok) {
      throw new Error('Erreur lors du chargement des images');
    }

    const data = await response.json();
    displayImages(data.images || []);

  } catch (error) {
    console.error('Erreur:', error);
    showToast('Erreur lors du chargement des images. Mode démo activé.', 'warning');
    // Afficher des images factices en cas d'erreur
    displayDummyImages();
  } finally {
    hideLoader('searchLoader');
  }
}

// Gérer la recherche d'images
async function handleSearch() {
  const query = elements.searchInput.value.trim();
  if (!query) {
    showToast('Veuillez entrer un terme de recherche', 'warning');
    return;
  }

  elements.searchButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Recherche...';
  elements.searchButton.disabled = true;

  state.currentSearchQuery = query;
  state.currentPage = 1;

  try {
    showLoader('searchLoader');
    elements.imageContainer.innerHTML = '';

    const searchType = elements.searchType.value;
    const color = elements.colorFilter.value;

    // Construire l'URL avec les paramètres
    let url = `${CONFIG.BACKEND_URL}/api/search?query=${encodeURIComponent(query)}&per_page=${CONFIG.DEFAULT_IMAGES_PER_PAGE}&page=${state.currentPage}`;

    if (searchType) {
      url += `&type=${searchType}`;
    }
    if (color) {
      url += `&color=${color}`;
    }

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error('Erreur lors de la recherche');
    }

    const data = await response.json();
    displayImages(data.images || []);

    // Afficher le bouton "Afficher plus" s'il y a assez de résultats
    elements.loadMoreBtn.style.display = data.images && data.images.length >= CONFIG.DEFAULT_IMAGES_PER_PAGE ? 'flex' : 'none';

  } catch (error) {
    console.error('Erreur de recherche:', error);
    showToast('Erreur lors de la recherche. Mode démo activé.', 'warning');
    displayDummyImages();
  } finally {
    hideLoader('searchLoader');
    elements.searchButton.innerHTML = '<i class="fas fa-search"></i> Rechercher';
    elements.searchButton.disabled = false;
  }
}

// Charger plus d'images
async function loadMoreImages() {
  if (!state.currentSearchQuery) return;

  state.currentPage++;

  try {
    showLoader('searchLoader');

    const searchType = elements.searchType.value;
    const color = elements.colorFilter.value;

    let url = `${CONFIG.BACKEND_URL}/api/search?query=${encodeURIComponent(state.currentSearchQuery)}&per_page=${CONFIG.DEFAULT_IMAGES_PER_PAGE}&page=${state.currentPage}`;

    if (searchType) url += `&type=${searchType}`;
    if (color) url += `&color=${color}`;

    const response = await fetch(url);

    if (!response.ok) throw new Error('Erreur lors du chargement');

    const data = await response.json();
    displayImages(data.images || [], true);

    if (!data.images || data.images.length < CONFIG.DEFAULT_IMAGES_PER_PAGE) {
      elements.loadMoreBtn.style.display = 'none';
    }

  } catch (error) {
    console.error('Erreur:', error);
    showToast('Erreur lors du chargement des images supplémentaires', 'error');
  } finally {
    hideLoader('searchLoader');
  }
}

// Afficher les images dans la galerie
function displayImages(images, append = false) {
  if (!images || images.length === 0) {
    if (!append) {
      elements.imageContainer.innerHTML = '<p class="no-results">Aucun résultat trouvé. Essayez une autre recherche.</p>';
    }
    return;
  }

  if (!append) {
    elements.imageContainer.innerHTML = '';
  }

  images.forEach(image => {
    const imageCard = createImageCard(image);
    elements.imageContainer.appendChild(imageCard);
  });
}

// Créer une carte d'image
function createImageCard(imageData) {
  const imageCard = document.createElement('div');
  imageCard.className = 'image-card';

  const image = document.createElement('div');
  image.className = 'image';

  const img = document.createElement('img');
  img.src = imageData.url || imageData.urls?.small || imageData.urls?.regular || 'https://via.placeholder.com/400x300?text=Image';
  img.alt = imageData.description || imageData.alt_description || 'Image';
  img.loading = 'lazy';

  img.style.opacity = '0';
  img.style.transition = 'opacity 0.3s ease-in-out';
  img.onload = () => {
    img.style.opacity = '1';
  };

  const imageInfo = document.createElement('div');
  imageInfo.className = 'image-info';

  const title = document.createElement('h3');
  title.className = 'image-title';
  title.textContent = imageData.description || imageData.alt_description || 'Sans titre';

  const meta = document.createElement('div');
  meta.className = 'image-meta';

  const author = document.createElement('span');
  author.textContent = imageData.user?.name || imageData.query || 'Seeker AI';

  const likes = document.createElement('span');
  likes.innerHTML = `<i class="fas fa-heart"></i> ${imageData.likes || Math.floor(Math.random() * 100)}`;

  meta.appendChild(author);
  meta.appendChild(likes);
  imageInfo.appendChild(title);
  imageInfo.appendChild(meta);

  image.appendChild(img);
  imageCard.appendChild(image);
  imageCard.appendChild(imageInfo);

  imageCard.addEventListener('click', () => openImageModal({
    url: imageData.url || imageData.urls?.regular || imageData.urls?.full,
    title: imageData.description || imageData.alt_description || 'Sans titre',
    description: imageData.description || '',
    downloadUrl: imageData.url || imageData.urls?.full,
    author: imageData.user?.name || 'Seeker AI'
  }));

  return imageCard;
}

// Afficher des images factices
function displayDummyImages() {
  const dummyImages = [];
  for (let i = 0; i < 12; i++) {
    dummyImages.push({
      id: `dummy-${i}`,
      url: `https://picsum.photos/400/300?random=${i}`,
      description: `Image ${i + 1}`,
      likes: Math.floor(Math.random() * 100),
      user: { name: 'Seeker AI' }
    });
  }
  displayImages(dummyImages);
}

// Gérer la génération d'image
async function handleGenerateImage() {
  const prompt = elements.aiPrompt.value.trim();

  if (!prompt) {
    showToast('Veuillez décrire l\'image que vous souhaitez générer', 'warning');
    return;
  }

  try {
    elements.generateImageBtn.disabled = true;
    elements.generateImageBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Génération...';
    showLoader('generateLoader');

    const style = elements.aiStyle.value;

    // Appel au backend
    const response = await fetch(`${CONFIG.BACKEND_URL}/api/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ prompt, style })
    });

    if (!response.ok) {
      throw new Error('Erreur lors de la génération');
    }

    // Si le backend retourne une image
    const blob = await response.blob();
    const imageUrl = URL.createObjectURL(blob);

    displayGeneratedImage(imageUrl, prompt);

  } catch (error) {
    console.error('Erreur de génération:', error);
    showToast('Génération d\'image non disponible. Utilisation d\'une image de démonstration.', 'info');

    // Image de démonstration
    const demoImageUrl = `https://picsum.photos/600/400?random=${Date.now()}`;
    displayGeneratedImage(demoImageUrl, prompt);

  } finally {
    hideLoader('generateLoader');
    elements.generateImageBtn.disabled = false;
    elements.generateImageBtn.innerHTML = '<i class="fas fa-magic"></i> Générer';
  }
}

// Afficher l'image générée
function displayGeneratedImage(imageUrl, prompt) {
  elements.generatedImages.innerHTML = `
    <div class="generated-image-card">
      <img src="${imageUrl}" alt="Image générée">
      <div class="generated-image-prompt">
        <strong>Prompt:</strong> ${prompt}
      </div>
      <div class="generated-image-actions">
        <button class="download-btn" onclick="downloadGeneratedImage('${imageUrl}', '${prompt}')">
          <i class="fas fa-download"></i> Télécharger
        </button>
      </div>
    </div>
  `;
}

// Télécharger l'image générée
function downloadGeneratedImage(imageUrl, prompt) {
  const a = document.createElement('a');
  a.href = imageUrl;
  a.download = `generated-${prompt.substring(0, 20).replace(/\s+/g, '-')}-${Date.now()}.jpg`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast('Téléchargement démarré', 'success');
}

// Fonctions pour la modal
function openImageModal(imageData) {
  state.currentImage = imageData;
  elements.modalImage.src = imageData.url;
  elements.modalTitle.textContent = imageData.title;
  elements.modalDescription.textContent = imageData.description || '';

  if (imageData.downloadUrl) {
    elements.downloadBtn.style.display = 'flex';
  } else {
    elements.downloadBtn.style.display = 'none';
  }

  elements.modal.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  elements.modal.classList.remove('show');
  document.body.style.overflow = '';

  setTimeout(() => {
    elements.modalImage.src = '';
    elements.modalTitle.textContent = '';
    elements.modalDescription.textContent = '';
    state.currentImage = null;
  }, 300);
}

async function downloadImage() {
  if (!state.currentImage) return;

  try {
    showToast('Préparation du téléchargement...', 'info');

    const a = document.createElement('a');
    a.href = state.currentImage.url;
    a.download = `image-${Date.now()}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    showToast('Téléchargement démarré', 'success');
  } catch (error) {
    console.error('Erreur de téléchargement:', error);
    window.open(state.currentImage.url, '_blank');
    showToast('Ouverture de l\'image dans un nouvel onglet', 'info');
  }
}

function shareImage() {
  if (!state.currentImage) return;

  if (navigator.share) {
    navigator.share({
      title: state.currentImage.title,
      text: state.currentImage.description,
      url: state.currentImage.url
    }).then(() => {
      showToast('Image partagée avec succès', 'success');
    }).catch(err => {
      console.error('Erreur de partage:', err);
      copyToClipboard(state.currentImage.url);
    });
  } else {
    copyToClipboard(state.currentImage.url);
  }
}

function generateSimilarImage() {
  if (!state.currentImage) return;

  // Passer à l'onglet de génération et remplir le prompt
  const generateTab = document.querySelector('[data-tab="generate"]');
  if (generateTab) {
    generateTab.click();
  }

  elements.aiPrompt.value = state.currentImage.description || state.currentImage.title || 'Image similaire';
  closeModal();

  showToast('Prompt prérempli. Cliquez sur "Générer" pour créer une image similaire.', 'info');
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Lien copié dans le presse-papiers', 'success');
  }).catch(err => {
    console.error('Erreur de copie:', err);
    showToast('Impossible de copier le lien', 'error');
  });
}

// Fonctions utilitaires
function showLoader(loaderId) {
  const loader = document.getElementById(loaderId);
  if (loader) loader.style.display = 'block';
}

function hideLoader(loaderId) {
  const loader = document.getElementById(loaderId);
  if (loader) loader.style.display = 'none';
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        document.body.removeChild(toast);
      }, 300);
    }, 3000);
  }, 100);
}

// Rendre les fonctions globales accessibles
window.downloadGeneratedImage = downloadGeneratedImage;