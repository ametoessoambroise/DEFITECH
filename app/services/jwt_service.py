import jwt
import datetime
from flask import current_app


class JWTService:
    @staticmethod
    def generate_token(user_id):
        """
        Génère un token JWT pour un utilisateur.
        """
        payload = {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
            "iat": datetime.datetime.utcnow(),
            "sub": str(user_id),  # PyJWT exige que le subject soit une string
        }
        return jwt.encode(
            payload, current_app.config.get("SECRET_KEY"), algorithm="HS256"
        )

    @staticmethod
    def decode_token(token):
        """
        Décode un token JWT et retourne l'ID de l'utilisateur.
        """
        try:
            print(f"🔐 Décodage token: {token[:50]}...")
            print(f"🔑 SECRET_KEY: {current_app.config.get('SECRET_KEY')[:20]}...")

            payload = jwt.decode(
                token, current_app.config.get("SECRET_KEY"), algorithms=["HS256"]
            )
            print(f"✅ Token décodé avec succès: user_id={payload['sub']}")
            return int(payload["sub"])  # Reconvertir en int
        except jwt.ExpiredSignatureError as e:
            print(f"⏰ Token expiré: {e}")
            return "Token expiré. Veuillez vous reconnecter."
        except jwt.InvalidTokenError as e:
            print(f"❌ Token invalide (InvalidTokenError): {e}")
            return "Token invalide. Veuillez vous reconnecter."
        except Exception as e:
            print(f"💥 Erreur inattendue: {type(e).__name__}: {e}")
            return str(e)
