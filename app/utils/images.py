import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

def optimize_and_save_image(image_bytes: bytes, filepath: str):
    """Converts image to JPEG, keeps 1024x1024, sets 85% quality."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(filepath, "JPEG", quality=85)
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")        logger.error(f"Error optimizing image: {e}")        logger.error(f"Error optimizing image: {e}")
