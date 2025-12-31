from flask import Blueprint, Response, render_template, make_response, request
from app.extensions import db
from sqlalchemy import text
import datetime

seo_bp = Blueprint("seo", __name__)


@seo_bp.route("/sitemap.xml", methods=["GET"])
def sitemap():
    """Génère dynamiquement le sitemap.xml basé sur routes_catalog"""
    try:
        # Récupérer les routes publiques (non-authentifiées ou accessibles à tous)
        # On privilégie les routes qui ne nécessitent pas de connexion pour le sitemap public
        sql = """
            SELECT url, category 
            FROM routes_catalog 
            WHERE roles LIKE '%public%' OR roles = '[]' OR roles IS NULL
            ORDER BY category, url
        """
        result = db.session.execute(text(sql))
        pages = []

        # Base URL de l'application dynamique
        base_url = request.url_root.rstrip("/")

        for row in result:
            pages.append(
                {
                    "loc": f"{base_url}{row[0]}",
                    "lastmod": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "changefreq": "weekly",
                    "priority": "0.8" if row[1] == "Général" else "0.5",
                }
            )

        sitemap_xml = render_template("seo/sitemap.xml", pages=pages)
        response = make_response(sitemap_xml)
        response.headers["Content-Type"] = "application/xml"
        return response

    except Exception as e:
        # Fallback minimaliste en cas d'erreur
        import logging

        logging.error(f"Erreur Sitemap: {e}")
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            mimetype="application/xml",
        )
