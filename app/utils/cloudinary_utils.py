import cloudinary
import cloudinary.uploader
import os
from flask import current_app


def configure_cloudinary():
    """Configures cloudinary using environment variables or app config"""
    cloudinary.config(
        cloud_name=os.environ.get(
            "CLOUDINARY_CLOUD_NAME",
            current_app.config.get("CLOUDINARY_CLOUD_NAME", "dmokvhpjt"),
        ),
        api_key=os.environ.get(
            "CLOUDINARY_API_KEY", current_app.config.get("CLOUDINARY_API_KEY")
        ),
        api_secret=os.environ.get(
            "CLOUDINARY_API_SECRET", current_app.config.get("CLOUDINARY_API_SECRET")
        ),
        secure=True,
    )


def upload_to_cloudinary(file_stream, filename, folder="general", resource_type="auto"):
    """
    Generic upload to Cloudinary.

    Args:
        file_stream: Binary stream or bytes
        filename: Name of the file
        folder: Cloudinary folder
        resource_type: 'image', 'raw', 'video', or 'auto'

    Returns:
        dict: Cloudinary upload result
    """
    configure_cloudinary()

    if hasattr(file_stream, "seek"):
        file_stream.seek(0)

    try:
        result = cloudinary.uploader.upload(
            file_stream,
            public_id=f"{folder}/{filename.split('.')[0]}_{os.urandom(4).hex()}",
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True,
        )
        return result
    except Exception as e:
        current_app.logger.error(f"Cloudinary upload error ({resource_type}): {str(e)}")
        raise e


def upload_cv_to_cloudinary(file_stream, filename, folder="cv_exports"):
    """Legacy helper for CVs (raw)"""
    return upload_to_cloudinary(file_stream, filename, folder, resource_type="raw")
