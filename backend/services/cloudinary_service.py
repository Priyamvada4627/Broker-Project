import cloudinary
import cloudinary.uploader
from ..config import settings

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True
)


def upload_verification_file(file_bytes: bytes, filename: str, deal_id: int) -> dict:
    """
    Upload a verification document to Cloudinary.
    Returns dict with 'url' and 'public_id'.
    Files are stored under: deal_documents/deal_{deal_id}/
    """
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=f"deal_documents/deal_{deal_id}",
        public_id=filename,
        resource_type="auto",          # handles PDFs, images, etc.
        overwrite=False,
        use_filename=True,
        unique_filename=True,
    )
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
    }


def delete_verification_file(public_id: str) -> None:
    """Delete a previously uploaded verification document from Cloudinary."""
    cloudinary.uploader.destroy(public_id, resource_type="auto")
