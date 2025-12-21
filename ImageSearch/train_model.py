import os
import json
import numpy as np
from PIL import Image
import pickle
from pathlib import Path
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from tensorflow import keras
    from tensorflow.keras import layers, regularizers, mixed_precision
    from tensorflow.keras.callbacks import (
        ModelCheckpoint,
        EarlyStopping,
        ReduceLROnPlateau,
        TensorBoard,
        LearningRateScheduler,
    )
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.applications import EfficientNetB0
    import tensorflow as tf

    # Activer la précision mixte pour améliorer les performances
    mixed_precision.set_global_policy("mixed_float16")

    # Optimiser TensorFlow
    tf.config.optimizer.set_jit(True)  # XLA compilation

    TENSORFLOW_AVAILABLE = True
except ImportError as e:
    logger.error(f"Bibliothèques manquantes: {e}")
    logger.info(
        "Installation: pip install tensorflow scikit-learn seaborn matplotlib pillow"
    )
    TENSORFLOW_AVAILABLE = False


@dataclass
class Config:
    """Configuration centralisée du système"""

    # Chemins
    data_dir: Path = Path("data/images")
    metadata_file: Path = Path("data/metadata.json")
    model_path: Path = Path("data/image_model.keras")
    label_encoder_path: Path = Path("data/label_encoder.pkl")
    tensorboard_dir: Path = Path("data/logs")

    # Hyperparamètres
    image_size: Tuple[int, int] = (224, 224)  # EfficientNet optimal
    batch_size: int = 32  # Augmenté pour efficacité
    epochs: int = 50
    initial_lr: float = 1e-3
    fine_tune_lr: float = 1e-5

    # Stratégie d'entraînement
    use_transfer_learning: bool = True
    use_mixed_precision: bool = True
    num_folds: int = 5
    early_stopping_patience: int = 10
    reduce_lr_patience: int = 5

    # Augmentation de données (plus agressive)
    augmentation_params: Dict = None

    def __post_init__(self):
        if self.augmentation_params is None:
            self.augmentation_params = {
                "rotation_range": 30,
                "width_shift_range": 0.25,
                "height_shift_range": 0.25,
                "shear_range": 0.2,
                "zoom_range": 0.25,
                "horizontal_flip": True,
                "vertical_flip": False,
                "brightness_range": [0.8, 1.2],
                "fill_mode": "nearest",
            }

        # Créer les répertoires nécessaires
        for path in [self.data_dir, self.tensorboard_dir]:
            path.mkdir(parents=True, exist_ok=True)


class DataLoader:
    """Chargeur de données optimisé avec cache"""

    def __init__(self, config: Config):
        self.config = config
        self._cache = {}

    def load_data(self) -> Tuple[np.ndarray, List[str], Dict[str, int]]:
        """
        Charger et prétraiter les données d'images

        Returns:
            images: Array numpy normalisé (N, H, W, 3)
            labels: Liste des labels
            label_to_index: Mapping label -> index
        """
        logger.info("📂 Chargement des données...")

        if not self.config.metadata_file.exists():
            logger.error("❌ Fichier de métadonnées introuvable")
            return np.array([]), [], {}

        with open(self.config.metadata_file, "r", encoding="utf-8") as f:
            metadata_list = json.load(f)

        images, labels = [], []
        loaded, skipped = 0, 0

        for metadata in metadata_list:
            query = metadata["query"]
            for image_data in metadata.get("results", []):
                image_id = image_data.get("id", "")
                image_filename = f"{query.replace(' ', '_')}_{image_id}.jpg"
                image_path = self.config.data_dir / image_filename

                if image_path.exists():
                    try:
                        img_array = self._load_and_preprocess_image(image_path)
                        images.append(img_array)
                        labels.append(query)
                        loaded += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur {image_path.name}: {e}")
                        skipped += 1
                else:
                    skipped += 1

        logger.info(f"✅ {loaded} images chargées, {skipped} ignorées")

        # Créer le mapping des labels avec comptage
        unique_labels = sorted(set(labels))
        label_to_index = {label: i for i, label in enumerate(unique_labels)}

        # Afficher la distribution des classes
        label_counts = {label: labels.count(label) for label in unique_labels}
        logger.info(f"🏷️ {len(unique_labels)} catégories détectées")
        for label, count in sorted(
            label_counts.items(), key=lambda x: x[1], reverse=True
        ):
            logger.info(f"  - {label}: {count} images")

        return np.array(images, dtype=np.float32), labels, label_to_index

    def _load_and_preprocess_image(self, image_path: Path) -> np.ndarray:
        """Charger et prétraiter une image avec cache"""
        cache_key = str(image_path)

        if cache_key in self._cache:
            return self._cache[cache_key]

        img = Image.open(image_path).convert("RGB")
        img = img.resize(self.config.image_size, Image.LANCZOS)
        img_array = np.array(img, dtype=np.float32) / 255.0

        self._cache[cache_key] = img_array
        return img_array


class ModelBuilder:
    """Constructeur de modèles avec architectures optimisées"""

    def __init__(self, config: Config):
        self.config = config

    def build_efficientnet_model(self, num_classes: int) -> keras.Model:
        """
        Construire un modèle basé sur EfficientNetB0 (meilleur que MobileNetV2)
        """
        logger.info("🏗️ Construction du modèle EfficientNetB0...")

        # Spécifier explicitement le format d'entrée RGB (3 canaux)
        input_shape = (*self.config.image_size, 3)
        logger.info(f"📐 Format d'entrée: {input_shape}")

        # Charger le modèle sans les poids ImageNet
        logger.info("🔧 Chargement du modèle sans poids ImageNet...")
        base_model = EfficientNetB0(
            weights=None,  # Ne pas charger les poids ImageNet
            include_top=False,
            input_shape=input_shape,
            pooling="avg",
        )

        # Geler initialement
        base_model.trainable = False
        
        # Afficher un résumé du modèle pour vérification
        base_model.summary(print_fn=logger.info)

        # Architecture optimisée
        inputs = keras.Input(shape=input_shape)
        x = base_model(inputs, training=False)
        x = layers.Dense(
            512, activation="relu", kernel_regularizer=regularizers.l2(1e-4)
        )(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.5)(x)
        x = layers.Dense(
            256, activation="relu", kernel_regularizer=regularizers.l2(1e-4)
        )(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.3)(x)
        outputs = layers.Dense(num_classes, activation="softmax", dtype="float32")(
            x
        )  # Float32 pour stabilité

        model = keras.Model(inputs, outputs)

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.config.initial_lr),
            loss="categorical_crossentropy",
            metrics=[
                "accuracy",
                keras.metrics.TopKCategoricalAccuracy(k=3, name="top3_acc"),
            ],
        )

        logger.info(f"✅ Modèle créé ({model.count_params():,} paramètres)")
        return model

    def build_custom_cnn(self, num_classes: int) -> keras.Model:
        """CNN personnalisé avec architecture moderne"""
        logger.info("🏗️ Construction du CNN personnalisé...")

        input_shape = (*self.config.image_size, 3)

        model = keras.Sequential(
            [
                # Block 1
                layers.Conv2D(64, 3, padding="same", input_shape=input_shape),
                layers.BatchNormalization(),
                layers.Activation("relu"),
                layers.Conv2D(64, 3, padding="same"),
                layers.BatchNormalization(),
                layers.Activation("relu"),
                layers.MaxPooling2D(2),
                layers.Dropout(0.25),
                # Block 2
                layers.Conv2D(128, 3, padding="same"),
                layers.BatchNormalization(),
                layers.Activation("relu"),
                layers.Conv2D(128, 3, padding="same"),
                layers.BatchNormalization(),
                layers.Activation("relu"),
                layers.MaxPooling2D(2),
                layers.Dropout(0.25),
                # Block 3
                layers.Conv2D(256, 3, padding="same"),
                layers.BatchNormalization(),
                layers.Activation("relu"),
                layers.Conv2D(256, 3, padding="same"),
                layers.BatchNormalization(),
                layers.Activation("relu"),
                layers.MaxPooling2D(2),
                layers.Dropout(0.25),
                # Classifier
                layers.GlobalAveragePooling2D(),
                layers.Dense(
                    512, activation="relu", kernel_regularizer=regularizers.l2(1e-4)
                ),
                layers.BatchNormalization(),
                layers.Dropout(0.5),
                layers.Dense(num_classes, activation="softmax", dtype="float32"),
            ]
        )

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.config.initial_lr),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )

        logger.info(f"✅ CNN créé ({model.count_params():,} paramètres)")
        return model

    def unfreeze_for_fine_tuning(self, model: keras.Model) -> keras.Model:
        """Dégeler le modèle pour fine-tuning"""
        logger.info("🔄 Préparation du fine-tuning...")

        # Dégeler progressivement (dernier 30% des couches)
        total_layers = (
            len(model.layers[0].layers)
            if hasattr(model.layers[0], "layers")
            else len(model.layers)
        )
        unfreeze_from = int(total_layers * 0.7)

        if hasattr(model.layers[0], "layers"):
            for layer in model.layers[0].layers[unfreeze_from:]:
                layer.trainable = True

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.config.fine_tune_lr),
            loss="sparse_categorical_crossentropy",
            metrics=[
                "accuracy",
                keras.metrics.TopKCategoricalAccuracy(k=3, name="top3_acc"),
            ],
        )

        logger.info(f"✅ {total_layers - unfreeze_from} couches dégelées")
        return model


class Trainer:
    """Gestionnaire d'entraînement avec stratégies avancées"""

    def __init__(self, config: Config):
        self.config = config
        self.data_loader = DataLoader(config)
        self.model_builder = ModelBuilder(config)

    def get_callbacks(self, fold: int) -> List:
        """Créer les callbacks d'entraînement"""
        callbacks = [
            ModelCheckpoint(
                str(self.config.model_path.parent / f"model_fold_{fold}.keras"),
                save_best_only=True,
                monitor="val_accuracy",
                mode="max",
                verbose=1,
            ),
            EarlyStopping(
                monitor="val_loss",
                patience=self.config.early_stopping_patience,
                restore_best_weights=True,
                verbose=1,
            ),
            ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=self.config.reduce_lr_patience,
                min_lr=1e-7,
                verbose=1,
            ),
            TensorBoard(
                log_dir=str(self.config.tensorboard_dir / f"fold_{fold}"),
                histogram_freq=0,
            ),
        ]

        return callbacks

    def create_data_generators(self, X_train: np.ndarray, y_train: np.ndarray):
        """Créer les générateurs d'augmentation de données"""
        datagen = ImageDataGenerator(**self.config.augmentation_params)
        datagen.fit(X_train)
        return datagen

    def train(self) -> Dict:
        """Entraîner le modèle avec validation croisée"""
        if not TENSORFLOW_AVAILABLE:
            logger.error("❌ TensorFlow indisponible")
            return {}

        logger.info("=" * 60)
        logger.info("🚀 ENTRAÎNEMENT DU MODÈLE")
        logger.info("=" * 60)

        # Charger les données
        images, labels, label_to_index = self.data_loader.load_data()

        if len(images) == 0:
            logger.error("❌ Aucune donnée disponible")
            return {}

        # Vérifier si suffisamment de données
        min_samples = 50
        if len(images) < min_samples:
            logger.warning(
                f"⚠️ Seulement {len(images)} images (minimum recommandé: {min_samples})"
            )

        # Encoder les labels
        y_encoded = np.array([label_to_index[label] for label in labels])

        # Choisir l'architecture
        num_classes = len(label_to_index)
        if self.config.use_transfer_learning:
            model = self.model_builder.build_efficientnet_model(num_classes)
        else:
            model = self.model_builder.build_custom_cnn(num_classes)

        # Split train/val
        from sklearn.model_selection import train_test_split

        X_train, X_val, y_train, y_val = train_test_split(
            images, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
        )

        logger.info(f"📊 Train: {len(X_train)}, Validation: {len(X_val)}")

        # Convertir les étiquettes en one-hot encoding
        from tensorflow.keras.utils import to_categorical
        y_train_one_hot = to_categorical(y_train, num_classes=num_classes)
        y_val_one_hot = to_categorical(y_val, num_classes=num_classes)

        # Générateur de données
        datagen = self.create_data_generators(X_train, y_train_one_hot)

        # Phase 1: Entraînement initial
        logger.info("\n🎯 Phase 1: Entraînement initial")
        history1 = model.fit(
            datagen.flow(X_train, y_train_one_hot, batch_size=self.config.batch_size),
            validation_data=(X_val, y_val_one_hot),
            epochs=self.config.epochs // 2,
            callbacks=self.get_callbacks(fold=0),
            verbose=1,
        )

        # Phase 2: Fine-tuning
        if self.config.use_transfer_learning:
            logger.info("\n🎯 Phase 2: Fine-tuning")
            model = self.model_builder.unfreeze_for_fine_tuning(model)
            history2 = model.fit(
                datagen.flow(X_train, y_train_one_hot, batch_size=self.config.batch_size),
                validation_data=(X_val, y_val_one_hot),
                epochs=self.config.epochs // 2,
                callbacks=self.get_callbacks(fold=1),
                verbose=1,
            )

        # Évaluation finale
        test_loss, test_acc, *other = model.evaluate(X_val, y_val_one_hot, verbose=0)
        logger.info(f"\n📊 Précision finale: {test_acc:.4f}")

        # Sauvegarder
        model.save(self.config.model_path)
        with open(self.config.label_encoder_path, "wb") as f:
            pickle.dump(label_to_index, f)

        logger.info(f"💾 Modèle sauvegardé: {self.config.model_path}")
        logger.info("✅ Entraînement terminé!")

        return {
            "accuracy": test_acc,
            "loss": test_loss,
            "num_classes": num_classes,
            "num_samples": len(images),
        }


class Predictor:
    """Prédicteur optimisé pour l'inférence"""

    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.label_to_index = None
        self.index_to_label = None

    def load_model(self):
        """Charger le modèle entraîné"""
        if not TENSORFLOW_AVAILABLE:
            logger.error("❌ TensorFlow indisponible")
            return False

        if not self.config.model_path.exists():
            logger.error(f"❌ Modèle introuvable: {self.config.model_path}")
            return False

        self.model = keras.models.load_model(self.config.model_path)

        with open(self.config.label_encoder_path, "rb") as f:
            self.label_to_index = pickle.load(f)

        self.index_to_label = {v: k for k, v in self.label_to_index.items()}

        logger.info("✅ Modèle chargé")
        return True

    def predict(self, image_path: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Prédire avec top-k résultats

        Returns:
            Liste de (label, confiance) triée par confiance
        """
        if self.model is None:
            if not self.load_model():
                return []

        # Prétraiter
        img = Image.open(image_path).convert("RGB")
        img = img.resize(self.config.image_size, Image.LANCZOS)
        img_array = np.array(img, dtype=np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # Prédire
        predictions = self.model.predict(img_array, verbose=0)[0]

        # Top-k
        top_indices = np.argsort(predictions)[-top_k:][::-1]
        results = [
            (self.index_to_label[idx], float(predictions[idx])) for idx in top_indices
        ]

        return results


def main():
    """Point d'entrée principal"""
    config = Config()
    trainer = Trainer(config)
    results = trainer.train()

    if results:
        logger.info("\n" + "=" * 60)
        logger.info("📊 RÉSUMÉ")
        logger.info("=" * 60)
        for key, value in results.items():
            logger.info(f"{key}: {value}")


if __name__ == "__main__":
    main()
