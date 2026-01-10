import qrcode
import io
import base64
import pdfkit
from flask import render_template, url_for
from app.models.academic import AcademicArchivedStudent
from app.services.academic_engine import AcademicEngine
from app.models.etudiant import Etudiant


class DocumentService:
    @staticmethod
    def generate_qr_code(data):
        """Génère un QR code en base64."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    @staticmethod
    def generate_transcript_pdf(student_id=None, archive_id=None, is_preview=False):
        """
        Génère le relevé de notes officiel en PDF.
        Peut être généré soit par ID étudiant (année courante/dernier archive)
        soit par ID d'archive spécifique.
        """
        data = None
        verify_url = ""

        # Cas 1: Génération par ID d'archive (Prioritaire pour l'historique)
        if archive_id:
            archive = AcademicArchivedStudent.query.get(archive_id)
            if archive:
                # Le template s'attend à un objet avec .user et .matricule (Etudiant)
                # On récupère l'objet Etudiant lié au User de l'archive
                student_obj = archive.student.etudiant if archive.student else None

                data = {
                    "student": student_obj,
                    "annee": archive.annee_academique,
                    "filiere": archive.filiere_nom,
                    "decision": archive.decision_jury,
                    "moyenne_generale": archive.moyenne_generale,
                    "credits_total": archive.credits_total_valides,
                    "details": archive.grades,
                    "is_official": True,
                }
                verify_url = url_for(
                    "main.verify_doc", doc_id=archive.id, _external=True
                )

        # Cas 2: Génération par ID étudiant (Année courante ou provisoire)
        elif student_id:
            student = Etudiant.query.get(student_id)
            if student:
                # Tenter de récupérer l'archive de l'année en cours
                archive = AcademicArchivedStudent.query.filter_by(
                    student_user_id=student.user_id, annee_academique=student.annee
                ).first()

                if archive:
                    data = {
                        "student": student,  # On passe l'objet Etudiant direct
                        "annee": archive.annee_academique,
                        "filiere": archive.filiere_nom,
                        "decision": archive.decision_jury,
                        "moyenne_generale": archive.moyenne_generale,
                        "credits_total": archive.credits_total_valides,
                        "details": archive.grades,
                        "is_official": True,
                    }
                    verify_url = url_for(
                        "main.verify_doc", doc_id=archive.id, _external=True
                    )
                else:
                    # Données provisoires
                    result = AcademicEngine.evaluate_student_progression(student_id)
                    if result:
                        data = {
                            "student": result["student"],  # On garde l'objet Etudiant
                            "annee": result["student"].annee,
                            "filiere": result["student"].filiere,
                            "decision": "PROVISOIRE",
                            "moyenne_generale": result["moyenne_generale"],
                            "credits_total": result["credits_total"],
                            "details": result["details"],
                            "is_official": False,
                        }
                        verify_url = "https://defitech.tg/verify/provisoire"

        if not data:
            return None

        # Génération QR Code
        qr_code_b64 = DocumentService.generate_qr_code(verify_url)

        # Rendu HTML pour PDF
        html_content = render_template(
            "documents/releve_notes.html",
            data=data,
            qr_code=qr_code_b64,
            verify_url=verify_url,
        )

        # Génération PDF via pdfkit (wkhtmltopdf)
        options = {
            "page-size": "A4",
            "encoding": "UTF-8",
            "margin-top": "0.75in",
            "margin-right": "0.75in",
            "margin-bottom": "0.75in",
            "margin-left": "0.75in",
        }

        # Configuration optionnelle du path si wkhtmltopdf n'est pas dans le PATH
        # config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf') # Exemple Linux
        # pdf = pdfkit.from_string(html_content, False, options=options, configuration=config)

        try:
            pdf_file = pdfkit.from_string(html_content, False, options=options)
            return pdf_file
        except Exception as e:
            print(f"Erreur PDFKit: {e}")
            return None
