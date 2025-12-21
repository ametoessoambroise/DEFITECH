import torch
from diffusers import AutoPipelineForText2Image

# Charger un modèle léger compatible CPU
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sd-turbo",
    torch_dtype=torch.float32
)

# Forcer l'exécution sur CPU
pipe = pipe.to("cpu")

# Optimisations RAM
pipe.enable_attention_slicing()

prompt =input("Votre prompt")

image = pipe(
    prompt,
    num_inference_steps=4,   # SD-Turbo fonctionne bien avec 2–4 steps
    guidance_scale=0.0       # Turbo n’utilise pas de CFG
).images[0]

image.save("output.png")
print("Image générée : output.png")
