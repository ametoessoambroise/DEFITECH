from train_model import predict_image

label, confidence = predict_image("images/affiche.png")
print(f"Label prédit : {label} ({confidence*100:.2f} %)")
