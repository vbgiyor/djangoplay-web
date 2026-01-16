import json
import logging
import random
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from utilities.utils.data_sync.load_env_and_paths import load_env_paths

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Generate line items for ISIC Rev. 5 industries and save to JSON in LINE_ITEM_JSON directory.
Expected .env keys: INDUSTRIES_JSON, LINE_ITEM_JSON
Example usage: ./manage.py generate_industry_line_items
JSON file is generated at LINE_ITEM_JSON/invoice_line_items.json
"""

    def add_arguments(self, parser):
        parser.add_argument('--min', type=int, default=1, help='Minimum number of line items per class (default: 1)')
        parser.add_argument('--max', type=int, default=5, help='Maximum number of line items per class (default: 5)')

    def generate_line_item_description(self, class_description, class_code, group_code, division_code, section_code):
        """Generate a line item description based on the ISIC class description with hierarchy code."""
        base_words = class_description.lower().split()
        action_words = ["supply of", "processing", "production of", "delivery of", "service for"]

        # Extract key nouns from description
        key_nouns = [word for word in base_words if len(word) > 3 and word not in ('and', 'other', 'activities')]
        if not key_nouns:
            key_nouns = ["item"]

        # Randomly select action and noun
        action = random.choice(action_words)
        noun = random.choice(key_nouns)

        # Construct hierarchy code
        hierarchy_code = f"{class_code}_{group_code}_{division_code}_{section_code}"
        return f"{action.capitalize()} {noun} - Code:{hierarchy_code}"

    def generate_line_items(self, class_data, group_code, division_code, section_code, min_items, max_items):
        """Generate 1-5 line items for a given ISIC class."""
        num_items = random.randint(min_items, max_items)
        line_items = {}
        for i in range(1, num_items + 1):
            key = str(i).zfill(2)
            line_items[key] = self.generate_line_item_description(
                class_data["Description"],
                class_data["Class"],
                group_code,
                division_code,
                section_code
            )
        return line_items

    def process_isic_data(self, isic_data, min_items, max_items):
        """Process ISIC JSON and add line items to each class."""
        for section in isic_data.get("isic", []):
            section_code = section.get("Section", "")
            for division in section.get("Divisions", []):
                division_code = division.get("Division", "")
                for group in division.get("Groups", []):
                    group_code = group.get("Group", "")
                    for class_data in group.get("Classes", []):
                        class_data["line_items"] = self.generate_line_items(
                            class_data,
                            group_code,
                            division_code,
                            section_code,
                            min_items,
                            max_items
                        )
        return isic_data

    def handle(self, *args, **options):
        start_time = time.time()
        User = get_user_model()
        try:
            admin_user = User.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using user: {admin_user.username}"))
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR("User with id=1 not found"))
            logger.error("User with id=1 not found")
            return

        stats = {'processed_classes': 0, 'skipped': [], 'total_line_items': 0}
        min_items = options['min']
        max_items = options['max']

        # Validate min and max
        if min_items < 1 or max_items < min_items or max_items > 5:
            self.stderr.write(self.style.ERROR("Invalid arguments: --min must be >= 1, --max must be >= --min and <= 5"))
            logger.error(f"Invalid arguments: min={min_items}, max={max_items}")
            return

        # Load environment paths
        env_data = load_env_paths(env_var='INDUSTRIES_JSON', require_exists=False)
        industries_json_path = env_data.get('INDUSTRIES_JSON')
        env_data_line_item = load_env_paths(env_var='LINE_ITEM_JSON', require_exists=False)
        line_item_json_path = env_data_line_item.get('LINE_ITEM_JSON')

        if not industries_json_path or not line_item_json_path:
            self.stderr.write(self.style.ERROR("INDUSTRIES_JSON or LINE_ITEM_JSON not defined in .env"))
            logger.error("INDUSTRIES_JSON or LINE_ITEM_JSON not defined")
            return

        # Read ISIC JSON
        try:
            with open(industries_json_path, 'r', encoding='utf-8') as f:
                isic_data = json.load(f)
            logger.info(f"Successfully loaded ISIC JSON from {industries_json_path}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading ISIC JSON from {industries_json_path}: {str(e)}"))
            logger.error(f"Error reading ISIC JSON: {str(e)}")
            return

        # Process ISIC data to add line items
        try:
            processed_data = self.process_isic_data(isic_data, min_items, max_items)
            # Count processed classes and line items
            for section in processed_data.get("isic", []):
                for division in section.get("Divisions", []):
                    for group in division.get("Groups", []):
                        for class_data in group.get("Classes", []):
                            stats['processed_classes'] += 1
                            stats['total_line_items'] += len(class_data.get("line_items", {}))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing ISIC data: {str(e)}"))
            logger.error(f"Error processing ISIC data: {str(e)}")
            stats['skipped'].append({'reason': str(e)})
            return

        # Save output JSON
        try:
            output_path = str(Path(line_item_json_path))
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=4, ensure_ascii=False)
            self.stdout.write(self.style.SUCCESS(f"Generated JSON at {output_path}"))
            logger.info(f"Generated JSON at {output_path}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error writing JSON to {output_path}: {str(e)}"))
            logger.error(f"Error writing JSON to {output_path}: {str(e)}")
            stats['skipped'].append({'reason': str(e)})
            return

        # Log and display summary
        self.stdout.write(self.style.SUCCESS(f"Generation Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f" - Processed classes: {stats['processed_classes']}")
        self.stdout.write(f" - Total line items: {stats['total_line_items']}")
        self.stdout.write(f" - Skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f" - Skipped: {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f" - ... and {len(stats['skipped']) - 5} more skipped")
        self.stdout.write(self.style.SUCCESS(f"Generation Completed in {time.time() - start_time:.2f}s"))
        logger.info(f"Generation Summary: Processed Classes={stats['processed_classes']}, Total Line Items={stats['total_line_items']}, Skipped={len(stats['skipped'])}")
