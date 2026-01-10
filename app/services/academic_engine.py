from app.models.etudiant import Etudiant
from app.models.note import Note
from app.models.matiere import Matiere
from app.models.filiere import Filiere
from app.models.academic import PromotionRule


class AcademicEngine:
    """
    Moteur de règles académiques pour DEFITECH.
    Gère le calcul des moyennes, la validation des crédits et la progression annuelle.
    """

    # Constantes pour les types d'évaluation
    TYPE_EXAMEN = ["examen", "exam", "partiel final", "final"]

    @staticmethod
    def _is_exam(type_eval):
        """Vérifie si le type d'évaluation correspond à un examen final."""
        if not type_eval:
            return False
        return type_eval.lower().strip() in AcademicEngine.TYPE_EXAMEN

    @staticmethod
    def calculate_subject_stats(student_id, subject_id):
        """
        Calcule la moyenne et les détails pour une matière donnée.
        Formule : (Somme(Devoirs + TP) * 0.40) + (Note Examen * 0.60)

        Retourne:
            dict: {
                "moyenne": float,
                "note_cc": float, # Moyenne ou Somme CC (selon interprétation, ici Somme car "Somme" demandé)
                "note_exam": float,
                "credits_obtenus": int,
                "is_validated": bool
            }
        """
        notes = Note.query.filter_by(
            etudiant_id=student_id, matiere_id=subject_id
        ).all()
        matiere = Matiere.query.get(subject_id)

        if not notes:
            return {
                "moyenne": 0.0,
                "note_cc": 0.0,
                "note_exam": 0.0,
                "note_devoir": 0.0,
                "note_tp": 0.0,
                "credits_obtenus": 0,
                "is_validated": False,
            }

        # Séparation CC et Examen
        notes_cc = []
        note_exam = 0.0
        note_devoir_sum = 0.0
        note_tp_sum = 0.0

        for n in notes:
            if n.note is None:
                continue

            type_lower = (n.type_evaluation or "").lower().strip()
            if AcademicEngine._is_exam(type_lower):
                note_exam = n.note
            elif "tp" in type_lower:
                note_tp_sum += n.note
                notes_cc.append(n.note)
            else:
                # On considère le reste comme "Devoir" par défaut (ou Devoir explicitement)
                note_devoir_sum += n.note
                notes_cc.append(n.note)

        # Calcul du CC (Somme des devoirs + TP)
        sum_cc = sum(notes_cc)

        moyenne = (sum_cc * 0.40) + (note_exam * 0.60)

        # Arrondi à 2 décimales
        moyenne = round(moyenne, 2)

        # Validation (Seuil par défaut 10, ou configurable via PromotionRule)
        rule = PromotionRule.query.filter_by(is_active=True).first()
        seuil = rule.seuil_moyenne_matiere if rule else 10.0

        is_validated = moyenne >= seuil
        credits_obtenus = matiere.credit if is_validated else 0

        return {
            "moyenne": moyenne,
            "note_cc": sum_cc,
            "note_exam": note_exam,
            "note_devoir": note_devoir_sum,
            "note_tp": note_tp_sum,
            "credits_obtenus": credits_obtenus,
            "is_validated": is_validated,
        }

    @staticmethod
    def evaluate_student_progression(student_id):
        """
        Évalue si l'étudiant peut passer en année supérieure.
        Règle : Total Crédits >= 45.
        """
        student = Etudiant.query.get(student_id)
        if not student:
            return None

        filiere_obj = Filiere.query.filter_by(nom=student.filiere).first()
        if not filiere_obj:
            return None

        # Récupérer toutes les matières de la filière pour filtrage robuste
        all_matieres_filiere = Matiere.query.filter_by(filiere_id=filiere_obj.id).all()

        # Filtrage intelligent de l'année (Gère "2eme annee" vs "2ème année")
        import unicodedata

        def normalize_str(s):
            if not s:
                return ""
            # Normalisation NFD pour séparer les accents
            s_norm = unicodedata.normalize("NFD", s)
            # Garder seulement les caractères non-diacritiques (pas d'accents)
            s_no_accent = "".join(c for c in s_norm if unicodedata.category(c) != "Mn")
            # Retirer espaces et mettre en minuscule
            return s_no_accent.lower().replace(" ", "").replace("-", "")

        student_annee_norm = normalize_str(student.annee)

        matieres = [
            m
            for m in all_matieres_filiere
            if normalize_str(m.annee) == student_annee_norm
        ]

        total_credits_possibles = 0
        total_credits_valides = 0
        moyenne_generale_cumul = 0.0
        details_matieres = []

        for m in matieres:
            stats = AcademicEngine.calculate_subject_stats(student.id, m.id)
            total_credits_possibles += m.credit
            total_credits_valides += stats["credits_obtenus"]
            moyenne_generale_cumul += stats["moyenne"]

            details_matieres.append({"matiere": m, "stats": stats})

        # Moyenne Générale / Score Global
        # Selon le retour utilisateur : "la moyenne générale c'est le total des crédit eu dans chaque matière"
        # Donc on utilise le total des crédits validés comme indicateur de performance.
        moyenne_generale = float(total_credits_valides)

        # Vérification règle 45 crédits
        rule = PromotionRule.query.filter_by(is_active=True).first()
        seuil_credits = rule.seuil_credits_passage if rule else 45

        decision = "REDOUBLEMENT"
        if total_credits_valides >= seuil_credits:
            decision = "ADMIS"

        return {
            "student": student,
            "credits_total": total_credits_valides,
            "credits_max": total_credits_possibles,
            "moyenne_generale": moyenne_generale,
            "decision": decision,
            "details": details_matieres,
        }
