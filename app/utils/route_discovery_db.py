"""
Module de découverte des routes depuis la base de données pour l'assistant IA
Permet à l'IA d'explorer dynamiquement les routes disponibles depuis la table routes_catalog
"""

import logging
import re
from typing import Dict, List, Any
from sqlalchemy import text

logger = logging.getLogger(__name__)


class RouteDiscoveryDB:
    """Découvre les routes depuis la base de données routes_catalog"""

    def __init__(self, db_session):
        self.db = db_session

    def discover_routes(
        self,
        user_role: str = None,
        keywords: str = None,
        category: str = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Découvre les routes disponibles selon les critères

        Args:
            user_role: Filtre par rôle (etudiant, enseignant, admin)
            keywords: Mots-clés pour rechercher dans descriptions et keywords
            category: Filtre par catégorie
            limit: Nombre maximum de résultats

        Returns:
            Dictionnaire avec les routes trouvées et métadonnées
        """
        try:
            # Construire la requête SQL
            query_conditions = []
            params = {}

            if user_role:
                query_conditions.append("roles LIKE :user_role")
                params["user_role"] = f"%{user_role}%"

            if keywords:
                keyword_conditions = []
                for keyword in keywords.split() if keywords else []:
                    keyword_conditions.append(
                        "(description LIKE :kw_{kw} OR keywords LIKE :kw_{kw})".format(
                            kw=len(keyword_conditions)
                        )
                    )
                    params[f"kw_{len(keyword_conditions)-1}"] = f"%{keyword}%"
                if keyword_conditions:
                    query_conditions.append(f"({' OR '.join(keyword_conditions)})")

            if category:
                query_conditions.append("category = :category")
                params["category"] = category

            where_clause = (
                f"WHERE {' AND '.join(query_conditions)}" if query_conditions else ""
            )

            # Requête principale
            sql_query = f"""
                SELECT url, description, roles, keywords, category
                FROM routes_catalog 
                {where_clause}
                ORDER BY 
                    CASE 
                        WHEN category = 'Authentification' THEN 1
                        WHEN category = 'Administration' THEN 2
                        WHEN category = 'Enseignement' THEN 3
                        WHEN category = 'API' THEN 4
                        ELSE 5
                    END,
                category, url
                LIMIT :limit
            """
            params["limit"] = limit

            result = self.db.execute(text(sql_query), params)
            routes = result.fetchall()

            # Grouper par catégorie
            routes_by_category = {}
            for route in routes:
                url, description, roles, keywords, category = route
                if category not in routes_by_category:
                    routes_by_category[category] = []

                routes_by_category[category].append(
                    {
                        "url": url,
                        "description": description,
                        "roles": roles,
                        "keywords": keywords,
                        "category": category,
                    }
                )

            # Obtenir les statistiques
            total_routes = self.db.execute(
                text("SELECT COUNT(*) FROM routes_catalog")
            ).scalar()
            categories = self.db.execute(
                text("SELECT DISTINCT category FROM routes_catalog ORDER BY category")
            ).fetchall()
            category_list = [cat[0] for cat in categories]
            logger.info(
                f"Routes trouvées: {routes}\n Routes par catégorie: {routes_by_category}\n Total de routes: {total_routes} \n Categories: {category_list}"
            )

            return {
                "success": True,
                "routes": routes_by_category,
                "total_found": len(routes),
                "total_available": total_routes,
                "categories": category_list,
                "filters_applied": {
                    "user_role": user_role,
                    "keywords": keywords,
                    "category": category,
                    "limit": limit,
                },
            }

        except Exception as e:
            logger.error(f"Erreur lors de la découverte des routes: {e}")
            return {"success": False, "error": str(e), "routes": {}, "total_found": 0}

    def search_routes_by_intent(
        self, user_intent: str, user_role: str
    ) -> Dict[str, Any]:
        """
        Recherche des routes basées sur l'intention de l'utilisateur

        Args:
            user_intent: Phrase décrivant ce que l'utilisateur veut faire
            user_role: Rôle de l'utilisateur

        Returns:
            Routes les plus pertinentes pour l'intention
        """
        try:
            # Extraire les mots-clés de l'intention
            intent_keywords = self._extract_keywords(user_intent)

            # Mapping d'intentions vers catégories
            intent_to_category = {
                "connexion": "Authentification",
                "inscription": "Authentification",
                "profil": "Profils utilisateurs",
                "notes": "Enseignement",
                "devoirs": "Enseignement",
                "cours": "Enseignement",
                "emploi": "Enseignement",
                "planning": "Planificateur d'études",
                "étude": "Planificateur d'études",
                "ressources": "Ressources numériques",
                "documents": "Ressources numériques",
                "communauté": "Communauté",
                "discussion": "Communauté",
                "chat": "Communauté",
                "cv": "Carrière & CV",
                "carrière": "Carrière & CV",
                "bug": "Rapports de bugs",
                "problème": "Rapports de bugs",
                "statistique": "Analytique & Statistiques",
                "analytique": "Analytique & Statistiques",
                "admin": "Administration",
                "gestion": "Administration",
                "visio": "Visioconférence",
                "réunion": "Visioconférence",
                "ia": "Assistant IA",
                "assistant": "Assistant IA",
            }

            # Déterminer la catégorie la plus probable
            probable_category = None
            for keyword, category in intent_to_category.items():
                if keyword in user_intent.lower():
                    probable_category = category
                    break

            # Rechercher avec priorité à la catégorie probable
            if probable_category:
                # 70% des résultats de la catégorie probable
                routes_result = self.discover_routes(
                    user_role=user_role,
                    keywords=user_intent,
                    category=probable_category,
                    limit=int(limit * 0.7) if (limit := 20) else 14,
                )

                # 30% des autres catégories
                other_routes_result = self.discover_routes(
                    user_role=user_role,
                    keywords=user_intent,
                    limit=int(limit * 0.3) if (limit := 20) else 6,
                )

                # Fusionner les résultats
                all_routes = {}
                for category, routes in routes_result.get("routes", {}).items():
                    if category not in all_routes:
                        all_routes[category] = []
                    all_routes[category].extend(routes)

                for category, routes in other_routes_result.get("routes", {}).items():
                    if category not in all_routes:
                        all_routes[category] = []
                    all_routes[category].extend(routes)
            else:
                # Recherche générale si aucune catégorie probable
                all_routes = self.discover_routes(
                    user_role=user_role, keywords=user_intent, limit=20
                ).get("routes", {})

            return {
                "success": True,
                "routes": all_routes,
                "intent": user_intent,
                "probable_category": probable_category,
                "keywords_extracted": intent_keywords,
            }

        except Exception as e:
            logger.error(f"Erreur lors de la recherche par intention: {e}")
            return {"success": False, "error": str(e), "routes": {}}

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés pertinents d'un texte"""
        # Mots à ignorer
        stop_words = {
            "le",
            "la",
            "les",
            "de",
            "des",
            "du",
            "pour",
            "avec",
            "une",
            "dans",
            "sur",
            "par",
            "est",
            "sont",
            "été",
            "elle",
            "nous",
            "vous",
            "leur",
            "ses",
            "son",
            "cette",
            "ces",
            "celui",
            "celle",
            "tout",
            "tous",
            "toute",
            "toutes",
            "je",
            "veux",
            "voudrais",
            "aimerais",
            "peut",
            "pourrais",
            "me",
            "mon",
            "ma",
            "mes",
        }

        # Extraire les mots significatifs
        words = re.findall(r"\b\w+\b", text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        return keywords[:10]  # Limiter à 10 mots-clés

    def get_route_suggestions(
        self, user_role: str, context: str = None
    ) -> List[Dict[str, Any]]:
        """
        Retourne des suggestions de routes basées sur le rôle et le contexte

        Args:
            user_role: Rôle de l'utilisateur
            context: Contexte supplémentaire (optionnel)

        Returns:
            Liste de routes suggérées
        """
        try:
            # Routes prioritaires par rôle
            priority_routes = {
                "etudiant": [
                    "Authentification",
                    "Enseignement",
                    "Planificateur d'études",
                    "Ressources numériques",
                    "Communauté",
                ],
                "enseignant": [
                    "Authentification",
                    "Enseignement",
                    "Ressources numériques",
                    "Communauté",
                    "Analytique & Statistiques",
                ],
                "admin": [
                    "Authentification",
                    "Administration",
                    "Analytique & Statistiques",
                    "Enseignement",
                    "Communauté",
                ],
            }

            suggested_routes = []
            priority_categories = priority_routes.get(user_role, ["Authentification"])

            for category in priority_categories:
                result = self.discover_routes(
                    user_role=user_role, category=category, limit=5
                )

                if result.get("success") and result.get("routes"):
                    for route in result["routes"].get(category, [])[
                        :2
                    ]:  # 2 routes par catégorie
                        suggested_routes.append(route)

            return suggested_routes[:10]  # Limiter à 10 suggestions

        except Exception as e:
            logger.error(f"Erreur lors de la génération de suggestions: {e}")
            return []
