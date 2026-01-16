import logging
from pathlib import Path
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from django.conf import settings

from utilities.ui.image_resize import resize_image_to_file


logger = logging.getLogger(__name__)


class InlineImageService:
    """
    ============================================================================
    INLINE IMAGE & ATTACHMENT SERVICE
    ----------------------------------------------------------------------------
    Extracted from CustomAccountAdapter to keep the adapter thin and make email
    rendering highly modular.

    Handles:
        - Brand logos (icon + text)
        - Signature profile photo
        - Contact icons (email, phone, etc.)
        - Arbitrary inline images
        - File attachments

    A newcomer to this codebase should immediately know that all email-related
    media lives here, not inside the Allauth adapter.

    Notes:
    ------
    • Each method is intentionally low-level and pure. It does NOT know
      anything about templates or email logic.
    • This keeps our system DRY: modify images here, and all emails update.
    ============================================================================
    """

    # ------------------------------------------------------------------
    # Generic inline image attachment
    # ------------------------------------------------------------------
    @staticmethod
    def attach_inline_image(
        msg,
        cid: str,
        src_path: Path,
        size: tuple | None = None,
        resized_dir: Path | None = None,
        dest_name: str | None = None,
    ):
        """
        Attach an inline image into an EmailMultiAlternatives message.

        Identical to previous `_attach_inline_image` in CustomAccountAdapter,
        but now reusable by all email types in the system.

        Arguments:
        ----------
        msg         : EmailMultiAlternatives instance
        cid         : str — Content-ID for inline embedding
        src_path    : Path — original file path
        size        : (w,h) optional resize target
        resized_dir : Path where resized images are cached
        dest_name   : final filename for resized variant
        """
        src_path = Path(src_path)
        if not src_path.is_file():
            logger.debug(
                "inline: source not found for cid=%s: %s",
                cid,
                src_path,
            )
            return

        path_to_attach = src_path

        # Resize if requested
        if size and resized_dir:
            resized_dir = Path(resized_dir)
            dest_name = dest_name or src_path.name
            try:
                resized_path = resize_image_to_file(src_path, resized_dir / dest_name, size=size)
                if resized_path:
                    path_to_attach = resized_path
            except Exception as e:
                logger.warning("inline: resize failed for %s → %s", src_path, e)

        try:
            with path_to_attach.open("rb") as f:
                data = f.read()
            img = MIMEImage(data, _subtype="png")
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=path_to_attach.name)
            msg.attach(img)
        except Exception as e:
            logger.warning(
                "inline: failed to attach %s as cid=%s: %s",
                path_to_attach,
                cid,
                e,
            )

    # ------------------------------------------------------------------
    # Logo attachments (icon + text) – used in all emails
    # ------------------------------------------------------------------
    @staticmethod
    def attach_logo(msg):
        """
        Attaches company brand logo:
            - icon (square)
            - text (wordmark)

        Originally: CustomAccountAdapter._attach_logo
        """
        base_path = Path(settings.BASE_DIR) / "paystream/static/elements/images/logo"

        icon_path = base_path / "logo_icon.png"
        InlineImageService.attach_inline_image(
            msg=msg,
            cid="djangoplay_logo_icon",
            src_path=icon_path,
        )

        text_path = base_path / "logotext.png"
        InlineImageService.attach_inline_image(
            msg=msg,
            cid="djangoplay_logo_text",
            src_path=text_path,
        )

    # ------------------------------------------------------------------
    # Profile signature image (for welcome emails)
    # ------------------------------------------------------------------
    @staticmethod
    def attach_signature_image(msg, size=(240, 240)):
        """
        Signature image shown in welcome emails.
        Originally: CustomAccountAdapter._attach_signature_image
        """
        base = Path(settings.BASE_DIR) / "paystream/static/elements/images/photo"
        src = base / "profile_photo.png"
        resized_dir = base / "resized"
        dest_name = f"{src.stem}.{size[0]}x{size[1]}.png"

        InlineImageService.attach_inline_image(
            msg=msg,
            cid="email_profile_photo",
            src_path=src,
            size=size,
            resized_dir=resized_dir,
            dest_name=dest_name,
        )

    # ------------------------------------------------------------------
    # Small contact icons (phone, email, location, GitHub, LinkedIn)
    # ------------------------------------------------------------------
    @staticmethod
    def attach_contact_icons(msg, size=(32, 32)):
        """
        Attach all small contact icons that appear in signature blocks.

        Originally: CustomAccountAdapter._attach_contact_icons
        """
        base = Path(settings.BASE_DIR) / "paystream/static/elements/images/icons"
        resized_dir = base / "resized"

        icon_map = [
            ("icon_phone", "phone.png"),
            ("icon_email", "email.png"),
            ("icon_location", "location.png"),
            ("icon_linkedin", "linkedin.png"),
            ("icon_github", "github.png"),
        ]

        for cid, filename in icon_map:
            InlineImageService.attach_inline_image(
                msg=msg,
                cid=cid,
                src_path=base / filename,
                size=size,
                resized_dir=resized_dir,
                dest_name=filename,
            )

    # ------------------------------------------------------------------
    # Generic file attachments (PDFs, exports, etc.)
    # ------------------------------------------------------------------
    @staticmethod
    def attach_file(msg, file_field, filename):
        """
        Attach a raw file (e.g., PDF export). Used across invoices, reports,
        and future document mailers.

        Originally: CustomAccountAdapter._attach_file
        """
        try:
            with file_field.open("rb") as f:
                payload = f.read()
            part = MIMEBase("application", "octet-stream")
            part.set_payload(payload)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename.rsplit("/", 1)[-1]}"',
            )
            msg.attach(part)
        except Exception as e:
            logger.error(
                "inline: failed to attach file %s: %s",
                filename,
                e,
            )
