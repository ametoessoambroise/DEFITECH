"""
Configuration des autorisations DefAI - Liste blanche des endpoints autorisés
Ce fichier définit les routes que DefAI peut accéder selon son rôle
"""

# Configuration des endpoints autorisés par catégorie et rôle
DEFAI_ALLOWED_ENDPOINTS = {
    # Routes de l'assistant IA (accessibles par tous les rôles)
    "ai": {
        "all": [
            "GET /ai/conversations",
            "POST /ai/conversations", 
            "GET /ai/conversations/<int:conversation_id>/messages",
            "POST /ai/chat",
            "POST /ai/upload",
            "GET /ai/dataset/stats",
            "DELETE /ai/conversations/<int:conversation_id>"
        ]
    },
    
    # Routes de données par rôle
    "role_data": {
        "etudiant": [
            "GET /api/role-data/etudiant/grades",
            "GET /api/role-data/etudiant/schedule",
            "GET /api/role-data/etudiant/assignments", 
            "GET /api/role-data/etudiant/notifications"
        ],
        
        "enseignant": [
            "GET /api/role-data/enseignant/classes",
            "GET /api/role-data/enseignant/subjects",
            "GET /api/role-data/enseignant/class-stats/<int:class_id>"
        ],
        
        "admin": [
            "GET /api/role-data/admin/platform-stats",
            "GET /api/role-data/admin/system-health",
            "GET /api/role-data/admin/users",
            "POST /api/role-data/admin/notify"
        ],
        
        "all": []  # Commun à tous les rôles
    },
    
    # Routes API générales
    "api": {
        "etudiant": [
            "GET /api/users/me",
            "GET /api/students/me",
            "GET /api/grades/me",
            "GET /api/schedule/me",
            "GET /api/notifications/me",
            "POST /api/notifications/read"
        ],
        
        "enseignant": [
            "GET /api/users/me",
            "GET /api/teachers/me",
            "GET /api/classes/my",
            "GET /api/students/by-class/<int:class_id>",
            "GET /api/grades/by-class/<int:class_id>",
            "POST /api/grades",
            "PUT /api/grades/<int:grade_id>",
            "GET /api/notifications/me",
            "POST /api/notifications/create"
        ],
        
        "admin": [
            "GET /api/users",
            "POST /api/users",
            "PUT /api/users/<int:user_id>",
            "DELETE /api/users/<int:user_id>",
            "GET /api/students",
            "POST /api/students", 
            "PUT /api/students/<int:student_id>",
            "DELETE /api/students/<int:student_id>",
            "GET /api/teachers",
            "POST /api/teachers",
            "PUT /api/teachers/<int:teacher_id>",
            "DELETE /api/teachers/<int:teacher_id>",
            "GET /api/courses",
            "POST /api/courses",
            "PUT /api/courses/<int:course_id>",
            "DELETE /api/courses/<int:course_id>",
            "GET /api/classes",
            "POST /api/classes",
            "PUT /api/classes/<int:class_id>",
            "DELETE /api/classes/<int:class_id>",
            "GET /api/grades/all",
            "POST /api/notify",
            "GET /api/system/stats",
            "POST /api/system/maintenance"
        ],
        
        "all": [
            "GET /api/health",
            "GET /api/version"
        ]
    }
}

# Mapping des rôles utilisateur vers les rôles DefAI
ROLE_MAPPING = {
    "etudiant": "etudiant",
    "enseignant": "enseignant", 
    "admin": "admin",
    # alias anglophones pour les appels DefAI
    "student": "etudiant",
    "teacher": "enseignant",
    "administrator": "admin",
}

# Alias supplémentaires acceptés dans les headers
ROLE_ALIASES = {
    "etudiant": "etudiant",
    "student": "etudiant",
    "eleve": "etudiant",
    "enseignant": "enseignant",
    "teacher": "enseignant",
    "professeur": "enseignant",
    "admin": "admin",
    "administrator": "admin",
    "administrateur": "admin",
}

def normalize_role(role: str) -> str:
    """
    Normalise un rôle provenant des headers DefAI.
    Retourne 'etudiant' par défaut si le rôle est inconnu.
    """
    if not role:
        return "etudiant"
    role_key = role.strip().lower()
    return ROLE_ALIASES.get(role_key, ROLE_MAPPING.get(role_key, "etudiant"))

# Configuration des timeouts et limites
DEFAI_CONFIG = {
    "max_request_size": 10 * 1024 * 1024,  # 10MB
    "request_timeout": 30,  # 30 secondes
    "rate_limit": {
        "requests_per_minute": 100,
        "burst_size": 20
    },
    "cache_ttl": 300,  # 5 minutes pour le cache anti-replay
    "signature_ttl": 300  # 5 minutes pour la validité des signatures
}

# Actions spéciales autorisées avec validation supplémentaire
SPECIAL_ACTIONS = {
    "delete_data": {
        "allowed_roles": ["admin"],
        "requires_confirmation": True,
        "log_level": "critical"
    },
    "modify_grades": {
        "allowed_roles": ["enseignant", "admin"],
        "requires_validation": True,
        "log_level": "warning"
    },
    "bulk_operations": {
        "allowed_roles": ["admin"],
        "requires_approval": True,
        "log_level": "warning"
    }
}

# Fonctions utilitaires pour la gestion des permissions
def get_allowed_endpoints_for_role(role: str) -> list:
    """Retourne la liste des endpoints autorisés pour un rôle donné"""
    normalized_role = normalize_role(role)
    allowed = []
    
    # Ajouter les endpoints communs à toutes les catégories
    for category in DEFAI_ALLOWED_ENDPOINTS:
        if "all" in DEFAI_ALLOWED_ENDPOINTS[category]:
            allowed.extend(DEFAI_ALLOWED_ENDPOINTS[category]["all"])
        
        if normalized_role in DEFAI_ALLOWED_ENDPOINTS[category]:
            allowed.extend(DEFAI_ALLOWED_ENDPOINTS[category][normalized_role])
    
    return allowed

def get_all_allowed_endpoints() -> dict:
    """Retourne la liste blanche complète, regroupée par rôle principal"""
    summary = {}
    for role in ("etudiant", "enseignant", "admin"):
        summary[role] = get_allowed_endpoints_for_role(role)
    return summary

def is_endpoint_allowed(role: str, method: str, path: str) -> tuple[bool, str]:
    """Vérifie si un endpoint est autorisé pour un rôle donné"""
    allowed_endpoints = get_allowed_endpoints_for_role(role)
    
    for endpoint in allowed_endpoints:
        endpoint_method, endpoint_path = endpoint.split(' ', 1)
        
        if method == endpoint_method:
            # Gestion des paramètres dynamiques
            if '<' in endpoint_path:
                import re
                pattern = endpoint_path.replace('<int:', '<').replace('<string:', '<')
                pattern = re.sub(r'<[^>]+>', '[^/]+', pattern)
                pattern = f"^{pattern}$"
                
                if re.match(pattern, path):
                    return True, "Endpoint autorisé"
            else:
                if path == endpoint_path:
                    return True, "Endpoint autorisé"
    
    return False, f"Endpoint {method} {path} non autorisé pour le rôle {role}"

def is_special_action_allowed(action: str, role: str) -> tuple[bool, dict]:
    """Vérifie si une action spéciale est autorisée et retourne les conditions"""
    if action not in SPECIAL_ACTIONS:
        return False, {"error": "Action inconnue"}
    
    action_config = SPECIAL_ACTIONS[action]
    allowed_roles = action_config.get("allowed_roles", [])
    
    if role not in allowed_roles:
        return False, {"error": f"Action {action} non autorisée pour le rôle {role}"}
    
    return True, action_config

# Configuration pour le logging
LOGGING_CONFIG = {
    "defai_access": {
        "level": "INFO",
        "format": "%(asctime)s - DefAI - %(levelname)s - %(message)s",
        "file": "logs/defai_access.log"
    },
    "defai_security": {
        "level": "WARNING", 
        "format": "%(asctime)s - DefAI-SECURITY - %(levelname)s - %(message)s",
        "file": "logs/defai_security.log"
    },
    "defai_errors": {
        "level": "ERROR",
        "format": "%(asctime)s - DefAI-ERROR - %(levelname)s - %(message)s", 
        "file": "logs/defai_errors.log"
    }
}
