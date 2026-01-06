"""
Module de découverte et d'accès aux routes pour l'assistant IA
Permet à l'IA d'explorer dynamiquement les routes disponibles et de récupérer des données
"""

import logging
import re
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class RouteDiscovery:
    """Découvre et catalogue les routes accessibles pour l'IA"""

    def __init__(self):
        self.route_catalog = {
            "etudiant": {
                "notes": {
                    "endpoint": "etudiant_voir_notes",
                    "url": "/etudiant/voir_notes",
                    "method": "GET",
                    "description": "Consulter toutes les notes de l'étudiant",
                    "data_type": "notes",
                    "keywords": ["notes", "résultats", "évaluations", "examens"],
                },
                "emploi_temps": {
                    "endpoint": "etudiant_emploi_temps",
                    "url": "/etudiant/emploi-temps",
                    "method": "GET",
                    "description": "Consulter l'emploi du temps",
                    "data_type": "schedule",
                    "keywords": ["emploi du temps", "cours", "horaires", "planning"],
                },
                "devoirs": {
                    "endpoint": "etudiant_devoirs",
                    "url": "/etudiant/devoirs",
                    "method": "GET",
                    "description": "Voir les devoirs et travaux à faire",
                    "data_type": "assignments",
                    "keywords": ["devoirs", "travaux", "à faire", "deadline"],
                },
                "dashboard": {
                    "endpoint": "dashboard",
                    "url": "/etudiant/dashboard",
                    "method": "GET",
                    "description": "Vue d'ensemble académique",
                    "data_type": "overview",
                    "keywords": [
                        "résumé",
                        "vue d'ensemble",
                        "statistiques",
                        "performance",
                    ],
                },
            },
            "enseignant": {
                "classes": {
                    "endpoint": "manage_etudiants",
                    "url": "/enseignant/mes-etudiants",
                    "method": "GET",
                    "description": "Liste des étudiants et classes",
                    "data_type": "students",
                    "keywords": ["étudiants", "classes", "élèves", "liste"],
                },
                "notes_gestion": {
                    "endpoint": "enseignant_notes",
                    "url": "/enseignant/notes",
                    "method": "GET",
                    "description": "Gestion des notes",
                    "data_type": "grades_management",
                    "keywords": ["notes", "évaluations", "notation", "résultats"],
                },
                "emploi_temps": {
                    "endpoint": "enseignant_emploi_temps",
                    "url": "/enseignant/emploi-temps",
                    "method": "GET",
                    "description": "Emploi du temps de l'enseignant",
                    "data_type": "schedule",
                    "keywords": ["emploi du temps", "cours", "horaires", "planning"],
                },
                "dashboard": {
                    "endpoint": "dashboard",
                    "url": "/enseignant/dashboard",
                    "method": "GET",
                    "description": "Vue d'ensemble enseignant",
                    "data_type": "overview",
                    "keywords": ["résumé", "vue d'ensemble", "statistiques"],
                },
            },
            "admin": {
                "utilisateurs": {
                    "endpoint": "admin_users",
                    "url": "/admin/users",
                    "method": "GET",
                    "description": "Gestion des utilisateurs",
                    "data_type": "users",
                    "keywords": ["utilisateurs", "users", "comptes", "inscriptions"],
                },
                "etudiants": {
                    "endpoint": "admin_etudiants",
                    "url": "/admin/etudiants",
                    "method": "GET",
                    "description": "Gestion des étudiants",
                    "data_type": "students",
                    "keywords": ["étudiants", "élèves", "apprenants"],
                },
                "enseignants": {
                    "endpoint": "admin_enseignants",
                    "url": "/admin/enseignants",
                    "method": "GET",
                    "description": "Gestion des enseignants",
                    "data_type": "teachers",
                    "keywords": ["enseignants", "professeurs", "profs"],
                },
                "filieres": {
                    "endpoint": "admin_filieres",
                    "url": "/admin/filieres",
                    "method": "GET",
                    "description": "Gestion des filières",
                    "data_type": "programs",
                    "keywords": ["filières", "programmes", "formations"],
                },
                "notes": {
                    "endpoint": "admin_notes",
                    "url": "/admin/notes",
                    "method": "GET",
                    "description": "Vue d'ensemble des notes",
                    "data_type": "grades",
                    "keywords": ["notes", "résultats", "évaluations"],
                },
                "dashboard": {
                    "endpoint": "admin_dashboard",
                    "url": "/admin/dashboard",
                    "method": "GET",
                    "description": "Tableau de bord administrateur",
                    "data_type": "overview",
                    "keywords": [
                        "résumé",
                        "vue d'ensemble",
                        "statistiques",
                        "dashboard",
                    ],
                },
            },
        }

    def get_available_routes(self, user_role: str) -> List[Dict]:
        """Retourne les routes disponibles pour un rôle"""
        routes = self.route_catalog.get(user_role, {})
        return [
            {
                "name": name,
                "endpoint": info["endpoint"],
                "method": info["method"],
                "description": info["description"],
                "data_type": info["data_type"],
                "keywords": info["keywords"],
                "url": info.get("url"),
            }
            for name, info in routes.items()
        ]

    def find_relevant_routes(self, query: str, user_role: str) -> List[Dict]:
        """Trouve les routes pertinentes pour une requête"""
        query_lower = query.lower()
        routes = self.route_catalog.get(user_role, {})
        relevant = []

        for name, info in routes.items():
            # Vérifier si des mots-clés correspondent
            for keyword in info["keywords"]:
                if keyword in query_lower:
                    relevant.append(
                        {
                            "name": name,
                            "endpoint": info["endpoint"],
                            "description": info["description"],
                            "data_type": info["data_type"],
                            "relevance_score": self._calculate_relevance(
                                query_lower, info["keywords"]
                            ),
                        }
                    )
                    break

        # Trier par score de pertinence
        relevant.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant

    def _calculate_relevance(self, query: str, keywords: List[str]) -> float:
        """Calcule un score de pertinence"""
        matches = sum(1 for keyword in keywords if keyword in query)
        return matches / len(keywords) if keywords else 0


class RouteAccessor:
    """Accède aux routes et extrait les données"""

    def __init__(self):
        self.discovery = RouteDiscovery()

    def fetch_route_data(
        self, endpoint: str, user_role: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Récupère les données d'une route en utilisant l'orchestrateur IA

        Args:
            endpoint: Le nom de la fonction dans l'orchestrateur (ex: get_student_grades)
            user_role: Le rôle de l'utilisateur
            params: Paramètres optionnels pour la requête

        Returns:
            Dict contenant les données ou une erreur
        """
        try:
            # Importer l'orchestrateur pour éviter les imports circulaires
            from app.services.ai_orchestrator import AIOrchestrator
            from flask_login import current_user

            # Créer une instance de l'orchestrateur
            orchestrator = AIOrchestrator()

            # Mapper les noms de endpoints vers les noms de fonctions de l'orchestrateur
            endpoint_mapping = {
                # Endpoints étudiant
                "etudiant_voir_notes": "get_student_grades",
                "dashboard": "get_student_grades_summary",
                "etudiant_emploi_du_temps": "get_student_schedule",
                "etudiant_notifications": "get_student_notifications",
                "etudiant_devoirs": "get_student_assignments",
                "etudiant_presence": "get_student_attendance",
                # Endpoints enseignant
                "enseignant_classes": "get_teacher_classes",
                "enseignant_notes_classe": "get_class_grades",
                "enseignant_statistiques": "get_class_statistics",
                # Endpoints admin
                "admin_dashboard": "get_platform_statistics",
                "admin_utilisateurs": "get_all_users",
            }

            # Obtenir le nom de la fonction de l'orchestrateur
            orchestrator_function = endpoint_mapping.get(endpoint, endpoint)

            # Exécuter la requête via l'orchestrateur
            result = orchestrator.execute_request(
                orchestrator_function, current_user.id, user_role
            )

            if result["success"]:
                return {
                    "success": True,
                    "data": result.get("data", {}),
                    "endpoint": endpoint,
                    "orchestrator_function": orchestrator_function,
                    "user_role": user_role,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Erreur inconnue"),
                    "endpoint": endpoint,
                    "orchestrator_function": orchestrator_function,
                }

        except Exception as e:
            logger.error(f"Erreur accès route {endpoint}: {e}")
            return {"success": False, "error": str(e), "endpoint": endpoint}

    def _parse_html_response(self, html: str, endpoint: str) -> Dict:
        """
        Parse une réponse HTML pour extraire les données structurées

        Cette méthode utilise des patterns spécifiques pour extraire
        les données des templates HTML
        """
        data = {"endpoint": endpoint, "extracted_data": {}}

        try:
            # Extraire les tableaux de données
            tables = self._extract_tables(html)
            if tables:
                data["extracted_data"]["tables"] = tables

            # Extraire les statistiques (nombres dans des cards/badges)
            stats = self._extract_statistics(html)
            if stats:
                data["extracted_data"]["statistics"] = stats

            # Extraire les listes
            lists = self._extract_lists(html)
            if lists:
                data["extracted_data"]["lists"] = lists

            # Extraire le texte principal
            main_text = self._extract_main_content(html)
            if main_text:
                data["extracted_data"]["main_content"] = main_text

        except Exception as e:
            logger.error(f"Erreur parsing HTML: {e}")
            data["parsing_error"] = str(e)

        return data

    def _extract_tables(self, html: str) -> List[Dict]:
        """Extrait les tableaux HTML"""
        tables = []
        # Pattern pour trouver les tables
        table_pattern = r"<table[^>]*>(.*?)</table>"
        table_matches = re.finditer(table_pattern, html, re.DOTALL | re.IGNORECASE)

        for match in table_matches:
            table_html = match.group(0)
            # Extraire les headers
            headers = re.findall(r"<th[^>]*>(.*?)</th>", table_html, re.DOTALL)
            headers = [re.sub(r"<.*?>", "", h).strip() for h in headers]

            # Extraire les lignes
            rows = []
            row_pattern = r"<tr[^>]*>(.*?)</tr>"
            row_matches = re.finditer(row_pattern, table_html, re.DOTALL)

            for row_match in row_matches:
                row_html = row_match.group(0)
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL)
                if cells:
                    cells = [re.sub(r"<.*?>", "", c).strip() for c in cells]
                    rows.append(cells)

            if headers and rows:
                tables.append({"headers": headers, "rows": rows})

        return tables

    def _extract_statistics(self, html: str) -> Dict:
        """Extrait les statistiques (nombres dans des cards)"""
        import re

        stats = {}
        # Pattern pour les cards de statistiques
        stat_patterns = [
            r'<div[^>]*class="[^"]*stat-card[^"]*"[^>]*>.*?<h3[^>]*>([^<]+)</h3>.*?<p[^>]*>([^<]+)</p>',
            r'<div[^>]*class="[^"]*badge[^"]*"[^>]*>([^<]+)</div>',
            r'<span[^>]*class="[^"]*count[^"]*"[^>]*>(\d+)</span>',
        ]

        for pattern in stat_patterns:
            matches = re.finditer(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    label = re.sub(r"<.*?>", "", groups[0]).strip()
                    value = re.sub(r"<.*?>", "", groups[1]).strip()
                    stats[label] = value

        return stats

    def _extract_lists(self, html: str) -> List[str]:
        """Extrait les listes à puces ou numérotées"""
        import re

        lists = []
        # Pattern pour les items de liste
        list_pattern = r"<li[^>]*>(.*?)</li>"
        matches = re.finditer(list_pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            item = re.sub(r"<.*?>", "", match.group(1)).strip()
            if item:
                lists.append(item)

        return lists

    def _extract_main_content(self, html: str) -> str:
        """Extrait le contenu principal textuel"""
        import re

        # Supprimer les scripts et styles
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

        # Extraire le texte de la zone de contenu principale
        main_pattern = r"<main[^>]*>(.*?)</main>"
        main_match = re.search(main_pattern, html, re.DOTALL | re.IGNORECASE)

        if main_match:
            content = main_match.group(1)
            # Supprimer toutes les balises HTML
            content = re.sub(r"<.*?>", "", content)
            # Nettoyer les espaces multiples
            content = re.sub(r"\s+", " ", content).strip()
            return content[:500]  # Limiter à 500 caractères

        return ""

    def analyze_query_and_fetch(self, query: str, user_role: str) -> Dict[str, Any]:
        """
        Analyse une requête utilisateur et récupère les données pertinentes

        Args:
            query: La question de l'utilisateur
            user_role: Le rôle de l'utilisateur

        Returns:
            Dict contenant les données récupérées de toutes les routes pertinentes
        """
        # Trouver les routes pertinentes
        relevant_routes = self.discovery.find_relevant_routes(query, user_role)

        if not relevant_routes:
            return {
                "success": False,
                "message": "Aucune route pertinente trouvée pour cette requête",
            }

        # Récupérer les données de toutes les routes pertinentes
        all_data = {"query": query, "routes_accessed": [], "combined_data": {}}

        for route in relevant_routes[:3]:  # Limiter à 3 routes max
            logger.info(f"Accès à la route: {route['endpoint']}")
            result = self.fetch_route_data(route["endpoint"], user_role)

            if result["success"]:
                all_data["routes_accessed"].append(
                    {
                        "endpoint": route["endpoint"],
                        "description": route["description"],
                        "data_type": route["data_type"],
                    }
                )
                all_data["combined_data"][route["data_type"]] = result["data"]

        all_data["success"] = len(all_data["routes_accessed"]) > 0
        return all_data
