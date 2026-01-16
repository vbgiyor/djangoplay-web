import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from entities.constants import ENTITY_TYPE_CHOICES
from entities.models import Entity
from fincore.constants import ADDRESS_TYPE_CHOICES
from fincore.models import Address, Contact, FincoreEntityMapping, TaxProfile
from industries.models import Industry
from locations.models import CustomCity, CustomCountry, CustomRegion, CustomSubRegion
from utilities.utils.data_sync.load_env_and_paths import load_env_paths
from utilities.utils.entities.entity_validations import is_valid_indian_pan, validate_gstin
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.postal_code_validations import validate_postal_code

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Import entity and fincore data from JSON files in ENTITIES_JSON/{COUNTRY_CODE} directory.
Expected .env keys: DATA_DIR, ENTITIES_JSON
Example usage: ./manage.py import_entities --country IN
JSON files are expected in ENTITIES_JSON/{COUNTRY_CODE}/{entity_name}.json
"""

    def add_arguments(self, parser):
        parser.add_argument('--country', type=str, default='NZ', help='Country code (e.g., NZ, IN)')
        parser.add_argument('--all', action='store_true', help='Import entities for all countries with JSON files')

    def load_json_file(self, json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json_file, json.load(f), None
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return json_file, None, str(e)

    def handle(self, *args, **options):
        start_time = time.time()

        # Get user for audit fields
        Employee = get_user_model()
        try:
            user = Employee.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using employee: {user.username} (ID: {user.id}) ({time.time() - start_time:.2f}s)"))
            logger.info(f"Using employee: {user.username}")
        except Employee.DoesNotExist:
            error_msg = f"Employee with id=1 not found. Please ensure user exists. ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        stats = {
            'entity': {'created': 0, 'updated': 0, 'skipped': []},
            'address': {'created': 0, 'updated': 0, 'skipped': []},
            'contact': {'created': 0, 'updated': 0, 'skipped': []},
            'tax_profile': {'created': 0, 'updated': 0, 'skipped': []},
            'fincore_entity_mapping': {'created': 0, 'updated': 0, 'skipped': []}
        }

        self.stdout.write(f"Starting import... ({time.time() - start_time:.2f}s)")
        logger.info("Starting entity and fincore data import")

        env_data = load_env_paths(env_var='ENTITIES_JSON', require_exists=False)
        entities_path = env_data.get('ENTITIES_JSON')
        if not entities_path:
            self.stderr.write(self.style.ERROR("ENTITIES_JSON not defined in .env"))
            logger.error("ENTITIES_JSON not defined")
            return

        # Cache related objects
        country_cache = {c.country_code: c for c in CustomCountry.objects.all()}
        region_cache = {r.id: r for r in CustomRegion.objects.filter(is_active=True)}
        subregion_cache = {s.id: s for s in CustomSubRegion.objects.filter(is_active=True)}
        industry_cache = {i.id: i for i in Industry.objects.all()}
        entity_cache = {e.id: e for e in Entity.objects.filter(is_active=True)}
        mapping_cache = {m.id: m for m in FincoreEntityMapping.objects.filter(is_active=True)}

        if options['all']:
            country_codes = [d.name for d in Path(entities_path).iterdir() if d.is_dir()]
            if not country_codes:
                self.stderr.write(self.style.ERROR("No country directories found in ENTITIES_JSON"))
                logger.error("No country directories found")
                return
        else:
            country_code = self.get_country_code(options['country'], country_cache)
            if not country_code:
                self.stderr.write(self.style.ERROR(f"Invalid country: {options['country']}"))
                logger.error(f"Invalid country input: {options['country']}")
                return
            country_codes = [country_code]

        for country_code in country_codes:
            country = country_cache.get(country_code)
            if not country:
                self.stderr.write(self.style.ERROR(f"Country {country_code} not found"))
                logger.error(f"Country with code {country_code} not found")
                stats['entity']['skipped'].append({
                    'entity': f"All entities in {country_code}",
                    'reason': f"Country {country_code} not found"
                })
                continue

            # Initialize city_cache for active cities in this country
            city_cache = {c.id: c for c in CustomCity.objects.filter(is_active=True, subregion__region__country_id=country.id)}

            country_path = Path(entities_path) / country_code
            if not country_path.is_dir():
                self.stderr.write(self.style.ERROR(f"Directory not found: {country_path}"))
                logger.error(f"Directory not found: {country_path}")
                stats['entity']['skipped'].append({
                    'entity': f"All entities in {country_code}",
                    'reason': f"Directory {country_path} not found"
                })
                continue

            json_files = list(country_path.glob("*.json"))
            if not json_files:
                self.stderr.write(self.style.WARNING(f"No JSON files found in: {country_path}"))
                logger.warning(f"No JSON files found in: {country_path}")
                continue

            self.stdout.write(f"Processing {len(json_files)} JSON files for {country_code}")
            logger.info(f"Found {len(json_files)} JSON files in {country_path}")

            # Parallel JSON loading
            with ThreadPoolExecutor(max_workers=4) as executor:
                json_results = list(executor.map(self.load_json_file, json_files))

            valid_results = [(jf, jd, err) for jf, jd, err in json_results if err is None]
            sorted_results = sorted(valid_results, key=lambda x: x[1]['entity'][0]['id'])

            has_hierarchy_changes = False
            for json_file, json_data, error in sorted_results:
                if error:
                    self.stderr.write(self.style.ERROR(f"Error reading {json_file}: {error}"))
                    logger.error(f"Error reading JSON file {json_file}: {error}")
                    stats['entity']['skipped'].append({
                        'entity': f"File {json_file.name}",
                        'reason': f"Error reading JSON: {error}"
                    })
                    continue

                # Inside the for json_file, json_data, error in sorted_results loop
                if not self.validate_json_data(json_data, stats, json_file, city_cache, country):
                    logger.error(f"Invalid JSON data in {json_file.name}")
                    continue

                with transaction.atomic():
                    entity_map = {}
                    entity_mapping_map = {}
                    default_address_map = {}

                    required_keys = {'entity', 'address', 'contact', 'tax_profile', 'fincore_entity_mapping'}
                    if not all(key in json_data for key in required_keys):
                        self.stderr.write(self.style.ERROR(f"Missing required keys in {json_file.name}: {required_keys - set(json_data.keys())}"))
                        logger.error(f"Missing required keys in {json_file.name}: {required_keys - set(json_data.keys())}")
                        stats['entity']['skipped'].append({
                            'entity': f"File {json_file.name}",
                            'reason': f"Missing required keys: {required_keys - set(json_data.keys())}"
                        })
                        continue

                    mapping_lookup = {m['entity_id']: m for m in json_data['fincore_entity_mapping']}
                    entity_lookup = {e['id']: e for e in json_data['entity']}

                    # Process fincore_entity_mapping
                    self.import_fincore_entity_mapping(json_data['fincore_entity_mapping'], entity_lookup, user, stats, entity_mapping_map, mapping_cache)

                    # Process addresses
                    self.import_address(json_data['address'], country, country_code, entity_mapping_map, user, stats, city_cache, region_cache, subregion_cache, default_address_map, json_file)

                    # Process entities
                    if self.import_entity(json_data['entity'], country, json_data, stats, entity_map, entity_mapping_map, default_address_map, user, industry_cache, entity_cache, mapping_lookup):
                        has_hierarchy_changes = True

                    # Process contacts
                    self.import_contact(json_data['contact'], country, country_code, entity_mapping_map, user, stats)

                    # Process tax profiles
                    self.import_tax_profile(json_data['tax_profile'], country, country_code, entity_mapping_map, user, stats, region_cache)

            if has_hierarchy_changes:
                try:
                    Entity._tree_manager.rebuild()
                    logger.info(f"Rebuilt MPTT tree for entities in {country_code}")
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Failed to rebuild MPTT tree for {country_code}: {str(e)}"))
                    logger.error(f"Failed to rebuild MPTT tree for {country_code}: {str(e)}")
                    return

        self.stdout.write(self.style.SUCCESS(f"Import Summary: ({time.time() - start_time:.2f}s)"))
        for model in stats:
            self.stdout.write(f"  - {model.replace('_', ' ').title()}:")
            self.stdout.write(f"    - Created: {stats[model]['created']}")
            self.stdout.write(f"    - Updated: {stats[model]['updated']}")
            self.stdout.write(f"    - Skipped: {len(stats[model]['skipped'])}")
            if stats[model]['skipped']:
                for skipped in stats[model]['skipped'][:5]:
                    reason = f"{skipped['reason']}"
                    if 'details' in skipped:
                        reason += f" (Details: {skipped['details']})"
                    self.stdout.write(f"      - {model.replace('_', ' ').title()} ID: {skipped.get(f'{model}_id', skipped.get('entity', 'Unknown'))}: {reason}")
                if len(stats[model]['skipped']) > 5:
                    self.stdout.write(f"      - ... and {len(stats[model]['skipped']) - 5} more skipped {model.replace('_', ' ')}")
        self.stdout.write(self.style.SUCCESS(f"Import Completed in {time.time() - start_time:.2f}s"))
        logger.info(f"Import Summary: {stats}")

    def get_country_code(self, country_input: str, country_cache) -> str | None:
        normalized_country = normalize_text(country_input).lower()
        country = next((c for c in country_cache.values() if
                        c.name.lower() == normalized_country or
                        c.asciiname.lower() == normalized_country or
                        c.country_code.lower() == normalized_country), None)
        if not country:
            self.stderr.write(self.style.ERROR(f"No country found for: {country_input}"))
            return None
        self.stdout.write(f"Proceeding with country '{country.name}'")
        return country.country_code

    def validate_json_data(self, json_data, stats, json_file, city_cache, country):
        required_keys = {'entity', 'address', 'contact', 'tax_profile', 'fincore_entity_mapping'}
        if not all(key in json_data for key in required_keys):
            missing = required_keys - set(json_data.keys())
            stats['entity']['skipped'].append({
                'entity': f"File {json_file.name}",
                'reason': f"Missing required keys: {missing}",
                'details': {'json_file': json_file.name}
            })
            return False

        for entity_data in json_data['entity']:
            if not entity_data.get('name'):
                stats['entity']['skipped'].append({
                    'entity': f"Entity ID {entity_data.get('id', 'Unknown')}",
                    'reason': "Missing name",
                    'details': {'json_file': json_file.name}
                })
                return False
            if entity_data.get('entity_type') not in dict(ENTITY_TYPE_CHOICES):
                stats['entity']['skipped'].append({
                    'entity': entity_data.get('name', 'Unknown'),
                    'reason': f"Invalid entity_type: {entity_data.get('entity_type')}",
                    'details': {'json_file': json_file.name}
                })
                return False

        for address_data in json_data['address']:
            if not address_data.get('city_id'):
                stats['address']['skipped'].append({
                    'address_id': address_data.get('id', 'Unknown'),
                    'reason': "Missing city_id",
                    'details': {'json_file': json_file.name}
                })
                return False
            if address_data.get('address_type') not in dict(ADDRESS_TYPE_CHOICES):
                stats['address']['skipped'].append({
                    'address_id': address_data.get('id', 'Unknown'),
                    'reason': f"Invalid address_type: {address_data.get('address_type')}",
                    'details': {'json_file': json_file.name}
                })
                return False
            city_id = address_data.get('city_id')
            if city_id not in city_cache:
                stats['address']['skipped'].append({
                    'address_id': address_data.get('id', 'Unknown'),
                    'reason': f"Active city with id {city_id} not found in country {country.country_code}",
                    'details': {'json_file': json_file.name}
                })
                logger.warning(f"Invalid city_id {city_id} in {json_file.name}")
                return False

        return True

    def import_entity(self, entity_data_list, country, json_data, stats, entity_map, entity_mapping_map, default_address_map, user, industry_cache, entity_cache, mapping_lookup):
        new_entities = []
        update_entities = []
        has_hierarchy_changes = False

        for entity_data in sorted(entity_data_list, key=lambda x: x.get('parent_id') or 0):
            entity_id = entity_data.get('id')
            external_id = entity_data.get('external_id')
            name = normalize_text(entity_data.get('name', ''))
            entity_type = entity_data.get('entity_type')

            # Check for existing entity with same name and entity_type
            if Entity.objects.filter(name=name, entity_type=entity_type, is_active=True).exclude(id=entity_id).exists():
                stats['entity']['skipped'].append({
                    'entity': name,
                    'reason': f"Entity with name '{name}' and type '{entity_type}' already exists"
                })
                logger.warning(f"Skipping entity {name} (ID: {entity_id}) due to duplicate name and entity_type")
                continue

            mapping_data = mapping_lookup.get(entity_id)
            if not mapping_data or mapping_data['id'] not in entity_mapping_map:
                stats['entity']['skipped'].append({
                    'entity': name,
                    'reason': f"No valid fincore_entity_mapping for entity {name}"
                })
                continue

            entity = entity_cache.get(entity_id) or Entity.objects.filter(Q(external_id=external_id) | Q(id=entity_id)).first()
            is_new = entity is None

            if is_new:
                entity = Entity(id=entity_id)
            else:
                base_slug = slugify(name)
                slug = base_slug
                suffix = 1
                while Entity.objects.filter(slug=slug).exclude(id=entity_id).exists():
                    slug = f"{base_slug}-{suffix}"
                    suffix += 1
                entity.slug = slug
                update_entities.append(entity)

            entity.name = name
            entity.entity_type = entity_data.get('entity_type')
            entity.status = entity_data.get('status')
            entity.external_id = external_id
            entity.website = entity_data.get('website')
            entity.registration_number = entity_data.get('registration_number')
            entity.entity_size = entity_data.get('entity_size')
            entity.notes = normalize_text(entity_data.get('notes', ''))
            entity.created_by = user
            entity.updated_by = user
            entity.is_active = entity_data.get('is_active', True)

            try:
                created_at = entity_data.get('created_at')
                entity.created_at = timezone.make_aware(datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S%z') if '%z' in created_at else datetime.strptime(created_at, '%Y-%m-%d'))
                entity.updated_at = timezone.now()
            except ValueError:
                entity.created_at = timezone.now()
                entity.updated_at = timezone.now()

            industry_id = entity_data.get('industry_id')
            if industry_id:
                industry = industry_cache.get(industry_id)
                if not industry:
                    stats['entity']['skipped'].append({
                        'entity': name,
                        'reason': f"Industry with id {industry_id} not found"
                    })
                    continue
                entity.industry = industry

            parent_id = entity_data.get('parent_id')
            if parent_id:
                has_hierarchy_changes = True
                parent = entity_map.get(parent_id) or entity_cache.get(parent_id) or Entity.objects.filter(id=parent_id).first()
                if not parent:
                    stats['entity']['skipped'].append({
                        'entity': name,
                        'reason': f"Parent entity with id {parent_id} not found"
                    })
                    continue
                entity.parent = parent
                entity_cache[parent.id] = parent

            default_address_id = entity_data.get('default_address_id')
            if default_address_id:
                default_address = default_address_map.get(mapping_data['id'])
                if default_address == default_address_id:
                    try:
                        address = Address.objects.get(id=default_address_id, is_active=True)
                        entity.default_address = address
                    except Address.DoesNotExist:
                        stats['entity']['skipped'].append({
                            'entity': name,
                            'reason': f"Default address with id {default_address_id} not found or inactive"
                        })
                        continue

            if not entity.name:
                stats['entity']['skipped'].append({
                    'entity': name,
                    'reason': "Entity name cannot be empty"
                })
                continue

            if is_new:
                new_entities.append(entity)
            entity_map[entity_id] = entity

        # Save new entities individually to ensure MPTT fields are set
        if new_entities:
            try:
                for entity in new_entities:
                    entity.save(user=user)  # Use save to trigger MPTT logic
                stats['entity']['created'] += len(new_entities)
                logger.info(f"Created {len(new_entities)} entities")
                for ent in new_entities:
                    entity_cache[ent.id] = ent
            except Exception as e:
                stats['entity']['skipped'].extend([{'entity': e.name, 'reason': str(e)} for e in new_entities])
                logger.error(f"Failed to create entities: {str(e)}")

        if update_entities:
            try:
                Entity.objects.bulk_update(
                    update_entities,
                    ['name', 'entity_type', 'status', 'external_id', 'website', 'registration_number', 'entity_size', 'notes', 'is_active', 'created_by', 'updated_by', 'created_at', 'updated_at', 'industry_id', 'parent_id', 'default_address_id', 'slug'],
                    batch_size=1000
                )
                stats['entity']['updated'] += len(update_entities)
                logger.info(f"Updated {len(update_entities)} entities")
                for ent in update_entities:
                    entity_cache[ent.id] = ent
            except Exception as e:
                stats['entity']['skipped'].extend([{'entity': e.name, 'reason': str(e)} for e in update_entities])
                logger.error(f"Failed to bulk update entities: {str(e)}")

        return has_hierarchy_changes

    def import_fincore_entity_mapping(self, mapping_data_list, entity_lookup, user, stats, entity_mapping_map, mapping_cache):
        new_mappings = []
        update_mappings = []

        for mapping_data in mapping_data_list:
            mapping_id = mapping_data.get('id')
            entity_id = mapping_data.get('entity_id')
            entity_type = mapping_data.get('entity_type', 'entities.Entity')

            if entity_id not in entity_lookup:
                stats['fincore_entity_mapping']['skipped'].append({
                    'mapping_id': mapping_id,
                    'reason': f"No entity found for entity_id {entity_id}"
                })
                continue

            mapping = mapping_cache.get(mapping_id) or FincoreEntityMapping.objects.filter(entity_type=entity_type, entity_id=entity_id).first()
            is_new = mapping is None

            if is_new:
                mapping = FincoreEntityMapping(id=mapping_id)
            else:
                update_mappings.append(mapping)

            mapping.entity_uuid = mapping_data.get('entity_uuid', str(uuid.uuid4()))
            mapping.entity_type = entity_type
            mapping.entity_id = entity_id
            mapping.content_type = 'entities.Entity'
            mapping.is_active = mapping_data.get('is_active', True)

            try:
                created_at = mapping_data.get('created_at')
                mapping.created_at = timezone.make_aware(datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S%z') if '%z' in created_at else datetime.strptime(created_at, '%Y-%m-%d'))
                mapping.updated_at = timezone.now()
            except ValueError:
                mapping.created_at = timezone.now()
                mapping.updated_at = timezone.now()

            if is_new:
                new_mappings.append(mapping)
            entity_mapping_map[mapping_id] = mapping

        if new_mappings:
            try:
                FincoreEntityMapping.objects.bulk_create(new_mappings, batch_size=1000)
                stats['fincore_entity_mapping']['created'] += len(new_mappings)
                logger.info(f"Created {len(new_mappings)} fincore entity mappings")
                for m in new_mappings:
                    mapping_cache[m.id] = m
            except Exception as e:
                stats['fincore_entity_mapping']['skipped'].extend([{'mapping_id': m.id, 'reason': str(e)} for m in new_mappings])
                logger.error(f"Failed to bulk create mappings: {str(e)}")

        if update_mappings:
            try:
                FincoreEntityMapping.objects.bulk_update(
                    update_mappings,
                    ['entity_uuid', 'entity_type', 'entity_id', 'content_type', 'is_active', 'created_at', 'updated_at'],
                    batch_size=1000
                )
                stats['fincore_entity_mapping']['updated'] += len(update_mappings)
                logger.info(f"Updated {len(update_mappings)} fincore entity mappings")
                for m in update_mappings:
                    mapping_cache[m.id] = m
            except Exception as e:
                stats['fincore_entity_mapping']['skipped'].extend([{'mapping_id': m.id, 'reason': str(e)} for m in update_mappings])
                logger.error(f"Failed to bulk update mappings: {str(e)}")

    def import_address(self, address_data_list, country, country_code, entity_mapping_map, user, stats, city_cache, region_cache, subregion_cache, default_address_map, json_file):
        new_addresses = []
        update_addresses = []
        address_cache = {a.id: a for a in Address.objects.filter(country_id=country.id, is_active=True)}

        for address_data in address_data_list:
            address_id = address_data.get('id')
            entity_mapping_id = address_data.get('entity_mapping_id')

            if address_data.get('country_id') != country.id:
                stats['address']['skipped'].append({
                    'address_id': address_id,
                    'reason': f"Invalid country_id: {address_data.get('country_id')} (expected {country.id})",
                    'details': {'entity_mapping_id': entity_mapping_id, 'json_file': json_file.name}
                })
                logger.warning(f"Skipping address {address_id} in {json_file.name}: Invalid country_id {address_data.get('country_id')}")
                continue

            entity_mapping = entity_mapping_map.get(entity_mapping_id)
            if not entity_mapping:
                stats['address']['skipped'].append({
                    'address_id': address_id,
                    'reason': f"FincoreEntityMapping with id {entity_mapping_id} not found",
                    'details': {'entity_mapping_id': entity_mapping_id, 'json_file': json_file.name}
                })
                logger.warning(f"Skipping address {address_id} in {json_file.name}: Entity mapping {entity_mapping_id} not found")
                continue

            city_id = address_data.get('city_id')
            city = city_cache.get(city_id)
            if not city:
                try:
                    city = CustomCity.objects.get(id=city_id, is_active=True, subregion__region__country_id=country.id)
                    city_cache[city_id] = city
                except CustomCity.DoesNotExist:
                    stats['address']['skipped'].append({
                        'address_id': address_id,
                        'reason': f"Active city with id {city_id} not found in country {country_code}",
                        'details': {'entity_mapping_id': entity_mapping_id, 'json_file': json_file.name}
                    })
                    logger.warning(f"Skipping address {address_id} in {json_file.name}: Active city ID {city_id} not found in country {country_code}")
                    continue

            address = address_cache.get(address_id) or Address.objects.filter(id=address_id, country_id=country.id, is_active=True).first()
            is_new = address is None

            if is_new:
                address = Address(id=address_id)
            else:
                update_addresses.append(address)

            postal_code = address_data.get('postal_code')
            try:
                if postal_code:
                    validate_postal_code(postal_code, country.country_code)
            except ValidationError as e:
                stats['address']['skipped'].append({
                    'address_id': address_id,
                    'reason': f"Invalid postal code: {str(e)}",
                    'details': {'entity_mapping_id': entity_mapping_id, 'json_file': json_file.name}
                })
                logger.warning(f"Skipping address {address_id} in {json_file.name}: Invalid postal code {postal_code}")
                continue

            address.entity_mapping = entity_mapping
            address.address_type = address_data.get('address_type', 'BILLING')
            address.street_address = normalize_text(address_data.get('street_address', '')) or 'Unknown Street'
            address.postal_code = postal_code
            address.is_default = address_data.get('is_default', False)
            address.created_by = user
            address.updated_by = user
            address.is_active = address_data.get('is_active', True)
            address.country = country
            address.city = city

            try:
                created_at = address_data.get('created_at')
                address.created_at = timezone.make_aware(datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S%z') if '%z' in created_at else datetime.strptime(created_at, '%Y-%m-%d'))
                address.updated_at = timezone.now()
            except ValueError:
                address.created_at = timezone.now()
                address.updated_at = timezone.now()

            region_id = address_data.get('region_id')
            if region_id:
                region = region_cache.get(region_id)
                if not region:
                    try:
                        region = CustomRegion.objects.get(id=region_id, is_active=True, country_id=country.id)
                        region_cache[region_id] = region
                    except CustomRegion.DoesNotExist:
                        logger.warning(f"Region ID {region_id} not found for address {address_id} in {json_file.name}, setting to null")
                        address.region = None
                    else:
                        address.region = region
                else:
                    address.region = region

            subregion_id = address_data.get('subregion_id')
            if subregion_id:
                subregion = subregion_cache.get(subregion_id)
                if not subregion:
                    try:
                        subregion = CustomSubRegion.objects.get(id=subregion_id, is_active=True, region__country_id=country.id)
                        subregion_cache[subregion_id] = subregion
                    except CustomSubRegion.DoesNotExist:
                        logger.warning(f"SubRegion ID {subregion_id} not found for address {address_id} in {json_file.name}, setting to null")
                        address.subregion = None
                    else:
                        address.subregion = subregion
                else:
                    address.subregion = subregion

            if is_new:
                new_addresses.append(address)
                address_cache[address_id] = address
            if address.is_default:
                default_address_map[entity_mapping_id] = address_id

        if new_addresses:
            try:
                Address.objects.bulk_create(new_addresses, batch_size=1000, ignore_conflicts=True)
                stats['address']['created'] += len(new_addresses)
                logger.info(f"Created {len(new_addresses)} addresses for {json_file.name}")
            except Exception as e:
                stats['address']['skipped'].extend([{'address_id': a.id, 'reason': str(e), 'details': {'entity_mapping_id': a.entity_mapping_id, 'json_file': json_file.name}} for a in new_addresses])
                logger.error(f"Failed to bulk create addresses for {json_file.name}: {str(e)}")
                raise

        if update_addresses:
            try:
                Address.objects.bulk_update(
                    update_addresses,
                    ['entity_mapping_id', 'address_type', 'street_address', 'postal_code', 'is_default', 'created_by', 'updated_by', 'is_active', 'country_id', 'city_id', 'region_id', 'subregion_id', 'created_at', 'updated_at'],
                    batch_size=1000
                )
                stats['address']['updated'] += len(update_addresses)
                logger.info(f"Updated {len(update_addresses)} addresses for {json_file.name}")
            except Exception as e:
                stats['address']['skipped'].extend([{'address_id': a.id, 'reason': str(e), 'details': {'entity_mapping_id': a.entity_mapping_id, 'json_file': json_file.name}} for a in update_addresses])
                logger.error(f"Failed to bulk update addresses for {json_file.name}: {str(e)}")
                raise

    def import_contact(self, contact_data_list, country, country_code, entity_mapping_map, user, stats):
        new_contacts = []
        update_contacts = []

        for contact_data in contact_data_list:
            contact_id = contact_data.get('id')
            entity_mapping_id = contact_data.get('entity_mapping_id')

            entity_mapping = entity_mapping_map.get(entity_mapping_id)
            if not entity_mapping:
                stats['contact']['skipped'].append({
                    'contact_id': contact_id,
                    'reason': f"FincoreEntityMapping with id {entity_mapping_id} not found",
                    'details': {'entity_mapping_id': entity_mapping_id}
                })
                continue

            contact = Contact.objects.filter(id=contact_id).first()
            is_new = contact is None

            if is_new:
                contact = Contact(id=contact_id)
            else:
                update_contacts.append(contact)

            phone_number = contact_data.get('phone_number')

            contact.entity_mapping = entity_mapping
            contact.name = normalize_text(contact_data.get('name', ''))
            contact.email = normalize_text(contact_data.get('email', ''))
            contact.phone_number = phone_number
            contact.role = contact_data.get('role')
            contact.is_primary = contact_data.get('is_primary', False)
            contact.created_by = user
            contact.updated_by = user
            contact.is_active = contact_data.get('is_active', True)
            contact.country = country

            try:
                created_at = contact_data.get('created_at')
                contact.created_at = timezone.make_aware(datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S%z') if '%z' in created_at else datetime.strptime(created_at, '%Y-%m-%d'))
                contact.updated_at = timezone.now()
            except ValueError:
                contact.created_at = timezone.now()
                contact.updated_at = timezone.now()

            if is_new:
                new_contacts.append(contact)

        if new_contacts:
            try:
                Contact.objects.bulk_create(new_contacts, batch_size=1000)
                stats['contact']['created'] += len(new_contacts)
                logger.info(f"Created {len(new_contacts)} contacts")
            except Exception as e:
                stats['contact']['skipped'].extend([{'contact_id': c.id, 'reason': str(e), 'details': {'entity_mapping_id': c.entity_mapping_id}} for c in new_contacts])
                logger.error(f"Failed to bulk create contacts: {str(e)}")

        if update_contacts:
            try:
                Contact.objects.bulk_update(
                    update_contacts,
                    ['entity_mapping_id', 'name', 'email', 'phone_number', 'role', 'is_primary', 'created_by', 'updated_by', 'is_active', 'country_id', 'created_at', 'updated_at'],
                    batch_size=1000
                )
                stats['contact']['updated'] += len(update_contacts)
                logger.info(f"Updated {len(update_contacts)} contacts")
            except Exception as e:
                stats['contact']['skipped'].extend([{'contact_id': c.id, 'reason': str(e), 'details': {'entity_mapping_id': c.entity_mapping_id}} for c in update_contacts])
                logger.error(f"Failed to bulk update contacts: {str(e)}")

    def import_tax_profile(self, tax_data_list, country, country_code, entity_mapping_map, user, stats, region_cache):
        new_tax_profiles = []
        update_tax_profiles = []

        for tax_data in tax_data_list:
            tax_id = tax_data.get('id')
            entity_mapping_id = tax_data.get('entity_mapping_id')

            entity_mapping = entity_mapping_map.get(entity_mapping_id)
            if not entity_mapping:
                stats['tax_profile']['skipped'].append({
                    'tax_profile_id': tax_id,
                    'reason': f"FincoreEntityMapping with id {entity_mapping_id} not found"
                })
                continue

            tax_profile = TaxProfile.objects.filter(id=tax_id).first()
            is_new = tax_profile is None

            if is_new:
                tax_profile = TaxProfile(id=tax_id)
            else:
                update_tax_profiles.append(tax_profile)

            tax_identifier = tax_data.get('tax_identifier')
            tax_identifier_type = tax_data.get('tax_identifier_type', 'GSTIN')
            if country_code == 'IN' and tax_identifier:
                if tax_identifier_type == 'GSTIN':
                    try:
                        validate_gstin(tax_identifier)
                    except ValidationError as e:
                        stats['tax_profile']['skipped'].append({
                            'tax_profile_id': tax_id,
                            'reason': f"Invalid GSTIN: {str(e)}"
                        })
                        continue
                    # Validate GSTIN state code against region
                    if tax_data.get('region_id'):
                        region = region_cache.get(tax_data['region_id'])
                        if region and tax_identifier[:2] != region.code:
                            stats['tax_profile']['skipped'].append({
                                'tax_profile_id': tax_id,
                                'reason': f"GSTIN state code {tax_identifier[:2]} does not match region code {region.code}"
                            })
                            continue
                elif tax_identifier_type == 'PAN':
                    if not is_valid_indian_pan(tax_identifier):
                        stats['tax_profile']['skipped'].append({
                            'tax_profile_id': tax_id,
                            'reason': f"Invalid PAN: {tax_identifier}"
                        })
                        continue

            tax_profile.entity_mapping = entity_mapping
            tax_profile.tax_identifier = tax_identifier or ''
            tax_profile.tax_identifier_type = tax_identifier_type
            tax_profile.is_tax_exempt = tax_data.get('is_tax_exempt', False)
            tax_profile.tax_exemption_reason = normalize_text(tax_data.get('tax_exemption_reason', '')) or (
                'Exempt per regulation' if tax_profile.is_tax_exempt else ''
            )
            tax_profile.tax_exemption_document = tax_data.get('tax_exemption_document')
            tax_profile.created_by = user
            tax_profile.updated_by = user
            tax_profile.is_active = tax_data.get('is_active', True)
            tax_profile.country = country

            try:
                created_at = tax_data.get('created_at')
                tax_profile.created_at = timezone.make_aware(datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S%z') if '%z' in created_at else datetime.strptime(created_at, '%Y-%m-%d'))
                tax_profile.updated_at = timezone.now()
            except ValueError:
                tax_profile.created_at = timezone.now()
                tax_profile.updated_at = timezone.now()

            region_id = tax_data.get('region_id')
            if region_id:
                region = region_cache.get(region_id)
                if not region:
                    try:
                        region = CustomRegion.objects.get(id=region_id)
                        region_cache[region_id] = region
                    except CustomRegion.DoesNotExist:
                        logger.warning(f"Region ID {region_id} not found for tax profile {tax_id}, setting to null")
                        tax_profile.region = None
                    else:
                        tax_profile.region = region
                else:
                    tax_profile.region = region

            if is_new:
                new_tax_profiles.append(tax_profile)

        if new_tax_profiles:
            try:
                TaxProfile.objects.bulk_create(new_tax_profiles, batch_size=1000)
                stats['tax_profile']['created'] += len(new_tax_profiles)
                logger.info(f"Created {len(new_tax_profiles)} tax profiles")
            except Exception as e:
                stats['tax_profile']['skipped'].extend([{'tax_profile_id': t.id, 'reason': str(e)} for t in new_tax_profiles])
                logger.error(f"Failed to bulk create tax profiles: {str(e)}")

        if update_tax_profiles:
            try:
                TaxProfile.objects.bulk_update(
                    update_tax_profiles,
                    ['entity_mapping_id', 'tax_identifier', 'tax_identifier_type', 'is_tax_exempt', 'tax_exemption_reason', 'tax_exemption_document', 'created_by', 'updated_by', 'is_active', 'country_id', 'region_id', 'created_at', 'updated_at'],
                    batch_size=1000
                )
                stats['tax_profile']['updated'] += len(update_tax_profiles)
                logger.info(f"Updated {len(update_tax_profiles)} tax profiles")
            except Exception as e:
                stats['tax_profile']['skipped'].extend([{'tax_profile_id': t.id, 'reason': str(e)} for t in update_tax_profiles])
                logger.error(f"Failed to bulk update tax profiles: {str(e)}")
