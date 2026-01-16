import unicodedata


def normalize_text(label):
        """Normalize text by removing diacritics."""
        if not label:
            return label
        normalized = ''.join(c for c in unicodedata.normalize('NFD', label) if unicodedata.category(c) != 'Mn')
        return normalized.strip()
