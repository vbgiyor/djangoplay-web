import argparse
import logging
import os
import re

# Set up logging for better feedback
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_models_from_app(project_path: str, app_name: str) -> set[str]:
    """
    Dynamically finds all model class names in a given Django app.

    Args:
        project_path (str): The absolute path to the Django project directory.
        app_name (str): The name of the Django app.

    Returns:
        Set[str]: A set of model class names found in the app.

    """
    models_path = os.path.join(project_path, app_name, 'models')
    models = set()

    if not os.path.isdir(models_path):
        logging.error(f"Models directory not found at: {models_path}")
        return models

    for file_name in os.listdir(models_path):
        if file_name.endswith('.py') and file_name != '__init__.py':
            file_path = os.path.join(models_path, file_name)
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # A simple regex to find model class definitions
            # Looks for "class SomeModel(Model, AnotherModel):"
            model_pattern = re.compile(r'class\s+(\w+)\s*\(')
            matches = model_pattern.findall(content)

            for match in matches:
                # Exclude classes that are likely abstract base classes
                if not match.endswith('Mixin') and not match.endswith('Model'):
                    models.add(match)
    return models

def fix_file(file_path: str, app_name: str, models_to_fix: set[str]) -> bool:
    """
    Analyzes a single Python file and fixes circular imports by moving them
    into the specific functions where the models are used.

    Args:
        file_path (str): The path to the file.
        app_name (str): The name of the Django app.
        models_to_fix (Set[str]): A set of model class names to fix.

    Returns:
        bool: True if the file was modified, False otherwise.

    """
    try:
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return False

    modified = False

    # Store imports to be moved, and the lines they were on
    imports_to_remove = {}

    # First pass: identify and remove top-level imports
    temp_lines = []
    for line in lines:
        is_import_to_remove = False
        for model_name in models_to_fix:
            # Create a dynamic regex pattern for the app and model name
            import_pattern = re.compile(
                rf'^\s*from\s+{re.escape(app_name)}.models.\w+\s+import\s+{re.escape(model_name)}\s*$'
            )
            if import_pattern.match(line):
                imports_to_remove[model_name] = line.strip()
                is_import_to_remove = True
                modified = True
                logging.info(f"Removed top-level import for '{model_name}' in {file_path}")
                break

        if not is_import_to_remove:
            temp_lines.append(line)

    if not imports_to_remove:
        return False

    # Second pass: re-insert imports into the functions where they are used
    final_lines = []
    block_buffer = []
    in_block = False
    block_indent = -1

    for line in temp_lines:
        stripped_line = line.strip()
        current_line_indent = len(line) - len(line.lstrip(' '))

        is_def_or_class = re.match(r'^\s*(def|class)\s+\w+.*?:', line)

        if is_def_or_class:
            if in_block:
                process_block(block_buffer, final_lines, imports_to_remove, file_path)

            in_block = True
            block_buffer = [line]
            block_indent = current_line_indent

        elif in_block and current_line_indent <= block_indent and stripped_line:
            process_block(block_buffer, final_lines, imports_to_remove, file_path)
            in_block = False
            block_buffer = []
            final_lines.append(line)

        elif in_block:
            block_buffer.append(line)

        else:
            final_lines.append(line)

    if in_block:
        process_block(block_buffer, final_lines, imports_to_remove, file_path)

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(final_lines)

    return modified

def process_block(block_buffer: list[str], final_lines: list[str], imports_to_remove: dict, file_path: str):
    """
    Helper function to process a block of code, add necessary imports,
    and append to the final lines list.
    """
    models_used_in_block = set()
    for block_line in block_buffer:
        for model_name in imports_to_remove.keys():
            if re.search(r'\b' + re.escape(model_name) + r'\b', block_line):
                models_used_in_block.add(model_name)

    if models_used_in_block:
        if block_buffer:
            insertion_index = -1
            indent = ""
            for i, line in enumerate(block_buffer):
                if re.match(r'^\s*(def|class)\s+\w+.*?:', line):
                    insertion_index = i + 1
                    indent = ' ' * (len(line) - len(line.lstrip(' ')))
                    break

            if insertion_index != -1:
                num_added = 0
                for model_name in sorted(models_used_in_block):
                    # Extract the module part from the original import line
                    original_import = imports_to_remove[model_name]
                    match = re.search(r'from (\S+) import', original_import)
                    if match:
                        model_module_path = match.group(1)
                        import_line = f"{indent}    from {model_module_path} import {model_name}\n"
                        block_buffer.insert(insertion_index + num_added, import_line)
                        num_added += 1
                        logging.info(f"Added import for '{model_name}' to a function in {file_path}")

                block_buffer.insert(insertion_index + num_added, f"{indent}\n")

    final_lines.extend(block_buffer)


def main():
    """
    Main function to scan the project and fix circular imports.
    """
    parser = argparse.ArgumentParser(description="Fix circular imports in a Django app.")
    parser.add_argument("--project", required=True, help="Absolute path to the Django project directory.")
    parser.add_argument("--app", required=True, help="Name of the Django app to fix.")

    args = parser.parse_args()

    project_path = args.project
    app_name = args.app

    # Get the list of models dynamically
    models_to_fix = get_models_from_app(project_path, app_name)
    if not models_to_fix:
        logging.error("Could not find any models to fix. Exiting.")
        return

    # Define the directory to scan based on the app name
    scan_dirs = [os.path.join(project_path, app_name, 'services')]

    fixed_files = []
    for dir_path in scan_dirs:
        if not os.path.isdir(dir_path):
            logging.error(f"Directory not found: {dir_path}")
            continue

        for root, _, files in os.walk(dir_path):
            for file_name in files:
                if file_name.endswith('.py'):
                    file_path = os.path.join(root, file_name)
                    if fix_file(file_path, app_name, models_to_fix):
                        fixed_files.append(file_path)

    if fixed_files:
        logging.info("\nRefactoring complete! The following files were updated:")
        for file in fixed_files:
            logging.info(f"- {file}")
    else:
        logging.info("No circular import patterns found in the specified directories.")

if __name__ == "__main__":
    main()
