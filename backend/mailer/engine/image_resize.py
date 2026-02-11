import logging
import os
import tempfile
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def resize_image_to_file(src_filepath, dest_filepath, size=(64, 64)):
    """
    Resize any image to `size` and save to `dest_filepath` (PNG).
    Behavior:
      - If dest exists and is newer than src, reuse it (skip resize).
      - Writes atomically (via temp file) to avoid half-written files.
    Returns Path(dest_filepath) or None on failure.
    """
    src = Path(src_filepath)
    dest = Path(dest_filepath)

    if not src.is_file():
        logger.warning(f"resize_image_to_file: source not found: {src}")
        return None

    # Ensure parent folder exists
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"resize_image_to_file: failed to create dest dir {dest.parent}: {e}")
        return None

    # Fast cache check by mtime
    try:
        if dest.is_file() and dest.stat().st_mtime >= src.stat().st_mtime:
            logger.debug(f"resize_image_to_file: using cached file {dest}")
            return dest
    except Exception as e:
        logger.debug(f"resize_image_to_file: mtime compare error: {e}")

    # Perform resize
    try:
        with Image.open(src).convert("RGBA") as img:
            if img.size == tuple(size):
                img_to_save = img
            else:
                img_to_save = img.resize(size, Image.LANCZOS)

            # Atomic write
            fd, tmp_path = tempfile.mkstemp(prefix="tmp_img_", dir=str(dest.parent))
            os.close(fd)
            try:
                img_to_save.save(tmp_path, format="PNG", optimize=True)
                os.replace(tmp_path, dest)
            except Exception:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                raise

        # Sync mtime
        try:
            src_mtime = src.stat().st_mtime
            os.utime(dest, (src_mtime, src_mtime))
        except Exception:
            pass

        logger.debug(f"resize_image_to_file: created {dest}")
        return dest

    except Exception as e:
        logger.error(f"resize_image_to_file: failed for {src} -> {dest}: {e}")
        return None
