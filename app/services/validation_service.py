from app.models.note import Note
from app.models.matiere import Matiere
from app.models.etudiant import Etudiant


class ValidationService:
    """
    Service centralisé pour tous les calculs de validation académique.
    """

    @staticmethod
    def get_notes(etudiant_id, matiere_id):
        return Note.query.filter_by(
            etudiant_id=etudiant_id, matiere_id=matiere_id
        ).all()

    @staticmethod
    def calcul_moyenne_matiere(etudiant_id, matiere_id):
        """
        Calcule la moyenne d'une matière pour un étudiant.
        Logique : Moyenne pondérée ou simple des notes 'normales'.
        Les rattrapages sont gérés séparément dans la validation.
        """
        notes = ValidationService.get_notes(etudiant_id, matiere_id)
        notes_normales = [n for n in notes if n.type_evaluation != "Rattrapage"]

        if not notes_normales:
            return 0.0

        # Exemple simple: moyenne arithmétique (à adapter si coeffs)
        total = sum(n.note for n in notes_normales if n.note is not None)
        count = len([n for n in notes_normales if n.note is not None])

        return total / count if count > 0 else 0.0

    @staticmethod
    def valider_matiere(etudiant_id, matiere_id):
        """
        Valide une matière selon les règles :
        - Moyenne >= 10 : VALIDÉ
        - Sinon, vérifie note de rattrapage.
        - Si Rattrapage existe : REMPLACE la note la plus basse des évaluations normales.
        """
        notes = ValidationService.get_notes(etudiant_id, matiere_id)
        notes_normales = [n for n in notes if n.type_evaluation != "Rattrapage"]
        note_rattrapage = next(
            (n for n in notes if n.type_evaluation == "Rattrapage"), None
        )

        # Calcul moyenne initiale
        valeurs_normales = [n.note for n in notes_normales if n.note is not None]
        if not valeurs_normales:
            moyenne_initiale = 0.0
        else:
            moyenne_initiale = sum(valeurs_normales) / len(valeurs_normales)

        if moyenne_initiale >= 10:
            return True, moyenne_initiale, "Validé"

        # Gestion Rattrapage
        if note_rattrapage and note_rattrapage.note is not None:
            # Logique : remplacer la note la plus basse
            if valeurs_normales:
                min_note = min(valeurs_normales)
                # On ne remplace que si le rattrapage est meilleur
                if note_rattrapage.note > min_note:
                    # On crèe une nouvelle liste virtuelle pour le calcul
                    nouvelles_valeurs = list(valeurs_normales)
                    nouvelles_valeurs.remove(min_note)
                    nouvelles_valeurs.append(note_rattrapage.note)
                    moyenne_rattrapage = sum(nouvelles_valeurs) / len(nouvelles_valeurs)

                    if moyenne_rattrapage >= 10:
                        return True, moyenne_rattrapage, "Validé après rattrapage"
                    else:
                        return False, moyenne_rattrapage, "Non validé après rattrapage"
                else:
                    # Rattrapage moins bon ou égal, pas de changement
                    return (
                        False,
                        moyenne_initiale,
                        "Non validé (Rattrapage insuffisant)",
                    )
            else:
                # Pas de notes normales, juste un rattrapage (cas bizarre mais possible)
                if note_rattrapage.note >= 10:
                    return True, note_rattrapage.note, "Validé (Rattrapage seul)"

        return (
            False,
            moyenne_initiale,
            "En attente de rattrapage" if moyenne_initiale < 10 else "Non validé",
        )

    @staticmethod
    def calculer_etat_academique(etudiant, annee):
        """
        Détermine l'état global de l'étudiant pour une année donnée.
        """
        # Récupérer toutes les matières de la filière/année
        from app.models.filiere import Filiere

        if not etudiant.filiere:
            return "INCONNU"

        filiere_obj = Filiere.query.filter_by(nom=etudiant.filiere).first()
        if not filiere_obj:
            return "INCONNU"

        # Récupération optimisée des matières pour la filière et l'année de l'étudiant
        matieres = Matiere.query.filter_by(
            filiere_id=filiere_obj.id, annee=etudiant.annee
        ).all()

        if not matieres:
            return "INSCRIT"

        matieres_echouees = []
        matieres_rattrapage = []

        for m in matieres:
            is_valid, moyenne, statut = ValidationService.valider_matiere(
                etudiant.id, m.id
            )
            if not is_valid:
                # Vérifier si c'est un échec définitif ou une attente de rattrapage
                # On considère "En attente de rattrapage" si aucun rattrapage n'a été saisi
                notes = ValidationService.get_notes(etudiant.id, m.id)
                has_rattrapage = any(n.type_evaluation == "Rattrapage" for n in notes)

                if has_rattrapage:
                    matieres_echouees.append(m)
                else:
                    matieres_rattrapage.append(m)

        if matieres_echouees:
            return "NON_VALIDE"
        elif matieres_rattrapage:
            return "ATTENTE_RATTRAPAGE"
        else:
            return "VALIDE"
