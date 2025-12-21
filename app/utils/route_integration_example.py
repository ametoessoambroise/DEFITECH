"""
Exemple d'intégration du système de découverte de routes pour l'IA
Montre comment l'IA peut utiliser RouteDiscoveryDB pour fournir des liens pertinents
"""

from app.extensions import db
from app.utils.route_discovery_db import RouteDiscoveryDB


def get_relevant_routes_for_user(user_intent: str, user_role: str) -> dict:
    """
    Fonction exemple que l'IA peut utiliser pour trouver des routes pertinentes

    Args:
        user_intent: Ce que l'utilisateur veut faire (ex: "voir mes notes")
        user_role: Rôle de l'utilisateur (etudiant, enseignant, admin)

    Returns:
        Dictionnaire avec les routes pertinentes et suggestions
    """
    # Créer l'instance de découverte
    discovery = RouteDiscoveryDB(db.session)

    # Rechercher les routes basées sur l'intention
    result = discovery.search_routes_by_intent(user_intent, user_role)

    if result["success"]:
        routes = result["routes"]

        # Formater les résultats pour l'affichage
        formatted_output = {
            "intent": user_intent,
            "probable_category": result.get("probable_category"),
            "routes_found": [],
            "total_found": 0,
        }

        for category, category_routes in routes.items():
            for route in category_routes:
                formatted_output["routes_found"].append(
                    {
                        "url": route["url"],
                        "description": route["description"],
                        "category": route["category"],
                        "roles": route["roles"],
                    }
                )

        formatted_output["total_found"] = len(formatted_output["routes_found"])

        return formatted_output
    else:
        return {"error": result["error"], "routes_found": [], "total_found": 0}


def demonstrate_usage():
    """Démonstration de l'utilisation du système"""

    examples = [
        ("je veux voir mes notes", "etudiant"),
        ("statistiques de ma classe", "enseignant"),
        ("gestion des utilisateurs", "admin"),
        ("modifier mon profil", "etudiant"),
        ("planifier mes études", "etudiant"),
        ("ressources pédagogiques", "enseignant"),
        ("signaler un bug", "etudiant"),
        ("visioconférence", "enseignant"),
    ]

    print("🔍 DÉMONSTRATION DU SYSTÈME DE DÉCOUVERTE DE ROUTES")
    print("=" * 60)

    for intent, role in examples:
        print(f"\n📝 Requête: '{intent}' (Rôle: {role})")
        print("-" * 40)

        result = get_relevant_routes_for_user(intent, role)

        if result.get("error"):
            print(f"❌ Erreur: {result['error']}")
        else:
            print(
                f"🎯 Catégorie probable: {result.get('probable_category', 'Non déterminée')}"
            )
            print(f"📊 Routes trouvées: {result['total_found']}")

            for i, route in enumerate(
                result["routes_found"][:3], 1
            ):  # Limiter à 3 pour la démo
                print(f"  {i}. 🔗 {route['url']}")
                print(f"📝 {route['description']}")
                print(f"🏷️  {route['category']} | 👥 {route['roles']}")
                print()


if __name__ == "__main__":
    # Tester avec le contexte Flask
    from wsgi import app

    with app.app_context():
        demonstrate_usage()
