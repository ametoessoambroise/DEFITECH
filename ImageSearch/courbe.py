import json
import matplotlib.pyplot as plt

with open("data/training_history.json", "r") as f:
    history = json.load(f)

plt.plot(history["accuracy"], label="Entraînement")
plt.plot(history["val_accuracy"], label="Validation")
plt.title("Évolution de la précision")
plt.legend()
plt.show()
