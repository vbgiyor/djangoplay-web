import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger('utilities.utils')

def load_env_paths(env_var=None, file=None, require_exists=True):
    """
    Load environment variables from .env file and resolve paths for DATA_DIR and the specified env_var.
    If env_var is provided, prefix DATA_DIR to its value if it is a relative path.
    Supports both file and directory paths for env_var.

    Args:
        env_var (str, optional): Environment variable to resolve (e.g., 'EMP_DATA', 'INVOICES_JSON').
        file (str, optional): Override path for the specified env_var.
        require_exists (bool, optional): If True, validate that the path exists. Default is True.

    Returns:
        dict: Dictionary containing resolved paths for DATA_DIR and env_var (if provided).
              Returns empty dict if critical paths are missing or invalid.

    """
    try:
        # Load .env file from project root or specified path
        env_path = Path(os.getenv('ENV_PATH', '.env')).resolve()
        logger.debug(f"Loading .env file from: {env_path}")

        if not env_path.exists():
            logger.warning(f".env file not found at: {env_path}")
            return {}

        load_dotenv(env_path)
        env_vars = {'DATA_DIR': os.getenv('DATA_DIR')}

        # Resolve and validate DATA_DIR
        if not env_vars['DATA_DIR']:
            logger.error("DATA_DIR is not set in .env")
            return {}

        env_vars['DATA_DIR'] = str(Path(os.path.expanduser(env_vars['DATA_DIR'])).resolve())
        # Verify DATA_DIR is writable
        try:
            os.makedirs(env_vars['DATA_DIR'], exist_ok=True)
            test_file = Path(env_vars['DATA_DIR']) / '.write_test'
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.debug(f"DATA_DIR is writable: {env_vars['DATA_DIR']}")
        except OSError as e:
            logger.error(f"DATA_DIR is not accessible or writable: {env_vars['DATA_DIR']} ({e})", exc_info=True)
            return {}

        # Handle specified env_var
        if env_var:
            env_vars[env_var] = file or os.getenv(env_var)
            if not env_vars[env_var]:
                logger.error(f"{env_var} not set in .env and no file provided")
                return {}

            # Resolve path: if file is provided, use it directly; otherwise, append to DATA_DIR if relative
            env_vars[env_var] = str(Path(env_vars[env_var]).resolve()) if file else str(Path(env_vars['DATA_DIR']) / env_vars[env_var].lstrip('/'))

            # Validate path exists (file or directory) only if required
            if require_exists:
                path_obj = Path(env_vars[env_var])
                if not (path_obj.is_file() or path_obj.is_dir()):
                    logger.error(f"Path does not exist or is neither a file nor a directory: {env_vars[env_var]}")
                    return {}
                logger.debug(f"Validated {env_var} as {'directory' if path_obj.is_dir() else 'file'}: {env_vars[env_var]}")

        # Log resolved paths
        logger.debug(f"Resolved paths: {', '.join(f'{k}={v}' for k, v in env_vars.items() if v)}")
        logger.info("\n✅ Environment variables and paths validated successfully.")
        return env_vars

    except Exception as e:
        logger.error(f"Error loading environment variables: {str(e)}", exc_info=True)
        return {}
