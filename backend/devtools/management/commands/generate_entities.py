import json
import logging
import random
import time
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.text import slugify
from entities.constants import ENTITY_STATUS_CHOICES, ENTITY_TYPE_CHOICES
from entities.models import Entity
from faker import Faker
from fincore.constants import ADDRESS_TYPE_CHOICES, CONTACT_ROLE_CHOICES, TAX_IDENTIFIER_TYPE_CHOICES
from fincore.models import Address, Contact, FincoreEntityMapping, TaxProfile
from industries.models import Industry
from locations.models import CustomCity, CustomCountry, CustomRegion
from utilities.utils.data_sync.companynames import CompanyNameGenerator
from utilities.utils.data_sync.load_env_and_paths import load_env_paths
from utilities.utils.entities.entities_status_ratio import ratio_distribution
from utilities.utils.entities.entity_validations import validate_gstin
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.general.phone_number_utils import generate_phone_number
from utilities.utils.general.postal_code_utils import generate_postal_code

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Generate entity and fincore data for specified country or all countries, save to JSON in ENTITIES_JSON/{COUNTRY_CODE} directory.
        Expected .env keys: DATA_DIR, ENTITIES_JSON
        Example usage:
        - ./manage.py generate_entities --country IN --count 200
        - ./manage.py generate_entities --country NZ --fixed
        - ./manage.py generate_entities --all --count 50
        - ./manage.py generate_entities --country IN --max 100
        JSON files are saved as ENTITIES_JSON/{COUNTRY_CODE}/{entity_name}.json
    """

    def add_arguments(self, parser):
        parser.add_argument('--country', type=str, default='IN', help='Country code (e.g., NZ, IN)')
        parser.add_argument('--count', type=int, default=10, help='Exact number of entities to generate per country')
        parser.add_argument('--min', type=int, default=3, help='Minimum entities per country if using --all without --count')
        parser.add_argument('--max', type=int, help='Maximum entities per country if count not specified')
        parser.add_argument('--all', action='store_true', help='Generate entities for all countries in database')
        parser.add_argument('--fixed', action='store_true', help='Generate exactly 10 entities with fixed status distribution (5 ACTIVE, 2 ON_HOLD, 1 PENDING, 1 SUSPENDED, 1 INACTIVE)')
        parser.add_argument('--random', action='store_true', help='Generate entities with random status distribution')

    def generate_email(self, contact_name, domain_name):
        clean_name = ''.join(c for c in normalize_text(contact_name).lower() if c.isalnum() or c in ['.', '_']).replace('..', '.').strip('.')
        return f"{clean_name or 'contact'}.{random.randint(100, 999)}@{domain_name}"

    def generate_gstin(self, region, entity_name):
        state_code = region.code.zfill(2) if region and hasattr(region, 'code') else '29'
        try:
            pan = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5)) + ''.join(random.choices('0123456789', k=4)) + 'P'
            entity_code = random.choice('123456789')
            gstin = f"{state_code}{pan}{entity_code}Z{random.choice('0123456789')}"
            validate_gstin(gstin)
            return gstin, pan
        except ValidationError:
            raise ValidationError(f"Failed to generate valid GSTIN for {entity_name}")

    def get_country_code(self, country_input: str) -> str | None:
        normalized_country = normalize_text(country_input).lower()
        try:
            country = CustomCountry.objects.filter(
                Q(name__iexact=normalized_country) | Q(asciiname__iexact=normalized_country) | Q(country_code__iexact=normalized_country),
                is_active=True
            ).first()
            if not country:
                self.stderr.write(self.style.ERROR(f"No country found for: {country_input}"))
                return None
            self.stdout.write(f"Proceeding with country '{country.name}'")
            return country.country_code
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error validating country: {str(e)}"))
            return None

    def generate_entity(self, fake, name_generator, country, country_code, regions, cities, industries, entity_types, statuses, company_sizes, address_types, contact_roles, tax_identifier_types, legal_statuses, generated_names, parent_entity, counters, user, is_fixed=False, generated_entities=None, potential_parents=None):
        for _ in range(10):
            # entity_name = name_generator.generate_name(org=name_generator._supported_keys(None))
            entity_name = name_generator.generate_name(org='rc',industry=None)
            normalized_name = normalize_text(entity_name)
            if normalized_name not in generated_names and not Entity.objects.filter(name=normalized_name, is_active=True).exists():
                break
        else:
            entity_name = f"{entity_name} {len(generated_names) + 1}"
            normalized_name = normalize_text(entity_name)
        generated_names.add(normalized_name)

        counters['entity'] += 1
        entity_id = counters['entity']
        external_id = f"{country_code}-{entity_id}"
        clean_name = ''.join(c for c in normalized_name.lower() if c.isalnum() or c == '-').replace('--', '-').strip('-') or 'company'
        website = f"https://www.{clean_name}.com"
        registration_number = fake.bban()[:10] if country_code == 'IN' else fake.bban()[:8]
        entity_type = random.choice(entity_types)
        status = random.choice(statuses)
        entity_size = random.choice(company_sizes)
        notes = normalize_text(fake.paragraph(nb_sentences=2))
        slug = slugify(normalized_name)
        industry = random.choice(industries) if industries else None
        city = random.choice(cities)
        region = city.subregion.region if city.subregion else None
        if not region or not city.subregion:
            logger.warning(f"Invalid address data for {normalized_name}: missing region or subregion")
            return None  # Skip entity if address data is incomplete
        postal_code = generate_postal_code(country_code)
        street_address = normalize_text(fake.street_address())

        selected_parent = parent_entity
        if not selected_parent and entity_type not in ('INDIVIDUAL', 'OTHER') and potential_parents:
            eligible_parents = [
                p for p in potential_parents
                if p['entity_type'] in ('BUSINESS', 'GOVERNMENT', 'NONPROFIT', 'PARTNERSHIP')
                and 'id' in p
                and (p['id'] in [e['id'] for e in generated_entities] or Entity.objects.filter(id=p['id'], is_active=True).exists())
            ]
            if eligible_parents:
                selected_parent = random.choice(eligible_parents)
            elif counters['entity'] > 1:
                logger.warning(f"No eligible parent found for entity {normalized_name} of type {entity_type} in {country_code}")

        now = timezone.now().strftime('%Y-%m-%d %H:%M:%S%z')
        counters['address'] += 1
        address_id = counters['address']
        addresses = [{
            "id": address_id,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
            "entity_mapping_id": None,
            "address_type": "HEADQUARTERS",
            "street_address": street_address,
            "city_id": city.id,
            "postal_code": postal_code,
            "country_id": country.id,
            "region_id": region.id,
            "subregion_id": city.subregion.id,
            "is_default": True,
            "created_by_id": user.id,
            "updated_by_id": user.id
        }]

        if entity_type in ('PARTNERSHIP', 'BUSINESS', 'GOVERNMENT', 'NONPROFIT'):
            counters['address'] += 1
            addresses.append({
                "id": counters['address'],
                "created_at": now,
                "updated_at": now,
                "is_active": True,
                "entity_mapping_id": None,
                "address_type": "OFFICE",
                "street_address": f"H.No. {random.randint(1, 999)} {city.name}",
                "city_id": city.id,
                "postal_code": generate_postal_code(country_code),
                "country_id": country.id,
                "region_id": region.id,
                "subregion_id": city.subregion.id,
                "is_default": False,
                "created_by_id": user.id,
                "updated_by_id": user.id
            })

        contact_name = fake.name()
        contact_email = self.generate_email(contact_name, f"{clean_name}.com")
        contact_phone = generate_phone_number(country_code)
        counters['contact'] += 1
        contacts = [{
            "id": counters['contact'],
            "created_at": now,
            "updated_at": now,
            "is_active": True,
            "entity_mapping_id": None,
            "name": normalize_text(contact_name),
            "email": contact_email,
            "phone_number": contact_phone,
            "role": random.choice(contact_roles),
            "country_id": country.id,
            "is_primary": True,
            "created_by_id": user.id,
            "updated_by_id": user.id
        }]

        tax_profiles = []
        if is_fixed and country_code == 'IN':
            try:
                gstin, pan = self.generate_gstin(region, normalized_name)
                if gstin[:2] != region.code.zfill(2):
                    raise ValidationError(f"GSTIN state code {gstin[:2]} does not match region code {region.code}")
                counters['tax'] += 1
                tax_profiles.append({
                    "id": counters['tax'],
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True,
                    "entity_mapping_id": None,
                    "tax_identifier": gstin,
                    "tax_identifier_type": "GSTIN",
                    "is_tax_exempt": random.choice([True, False]),
                    "tax_exemption_reason": normalize_text(fake.sentence()) if random.choice([True, False]) else "",
                    "tax_exemption_document": None,
                    "country_id": country.id,
                    "region_id": region.id,
                    "created_by_id": user.id,
                    "updated_by_id": user.id
                })
                counters['tax'] += 1
                tax_profiles.append({
                    "id": counters['tax'],
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True,
                    "entity_mapping_id": None,
                    "tax_identifier": pan,
                    "tax_identifier_type": "PAN",
                    "is_tax_exempt": False,
                    "tax_exemption_reason": "",
                    "tax_exemption_document": None,
                    "country_id": country.id,
                    "region_id": region.id,
                    "created_by_id": user.id,
                    "updated_by_id": user.id
                })
            except ValidationError as e:
                logger.warning(f"Skipping entity {normalized_name} due to tax profile error: {str(e)}")
                return None
        elif country_code == 'IN' and entity_type in ('BUSINESS', 'GOVERNMENT', 'NONPROFIT', 'PARTNERSHIP', 'SOLE_PROPRIETORSHIP'):
            try:
                gstin, pan = self.generate_gstin(region, normalized_name)
                if gstin[:2] != region.code.zfill(2):
                    raise ValidationError(f"GSTIN state code {gstin[:2]} does not match region code {region.code}")
                counters['tax'] += 1
                tax_profiles.append({
                    "id": counters['tax'],
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True,
                    "entity_mapping_id": None,
                    "tax_identifier": gstin,
                    "tax_identifier_type": "GSTIN",
                    "is_tax_exempt": random.choice([True, False]),
                    "tax_exemption_reason": normalize_text(fake.sentence()) if random.choice([True, False]) else "",
                    "tax_exemption_document": None,
                    "country_id": country.id,
                    "region_id": region.id,
                    "created_by_id": user.id,
                    "updated_by_id": user.id
                })
                counters['tax'] += 1
                tax_profiles.append({
                    "id": counters['tax'],
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True,
                    "entity_mapping_id": None,
                    "tax_identifier": pan,
                    "tax_identifier_type": "PAN",
                    "is_tax_exempt": False,
                    "tax_exemption_reason": "",
                    "tax_exemption_document": None,
                    "country_id": country.id,
                    "region_id": region.id,
                    "created_by_id": user.id,
                    "updated_by_id": user.id
                })
            except ValidationError as e:
                logger.warning(f"Skipping entity {normalized_name} due to tax profile error: {str(e)}")
                return None
        else:
            available_tax_types = [t for t in tax_identifier_types if t in ('VAT', 'EIN', 'OTHER')]
            if is_fixed or available_tax_types:
                counters['tax'] += 1
                tax_profiles.append({
                    "id": counters['tax'],
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True,
                    "entity_mapping_id": None,
                    "tax_identifier": fake.bban()[:15] if available_tax_types else '',
                    "tax_identifier_type": random.choice(available_tax_types) if available_tax_types else '',
                    "is_tax_exempt": random.choice([True, False]),
                    "tax_exemption_reason": normalize_text(fake.sentence()) if random.choice([True, False]) else "",
                    "tax_exemption_document": None,
                    "country_id": country.id,
                    "region_id": region.id,
                    "created_by_id": user.id,
                    "updated_by_id": user.id
                })

        counters['mapping'] += 1
        mapping_id = counters['mapping']
        entity_mapping = {
            "id": mapping_id,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
            "entity_uuid": str(uuid.uuid4()),
            "entity_type": "entities.Entity",
            "entity_id": entity_id
        }

        for addr in addresses:
            addr['entity_mapping_id'] = mapping_id
        for cont in contacts:
            cont['entity_mapping_id'] = mapping_id
        for tax in tax_profiles:
            tax['entity_mapping_id'] = mapping_id

        entity_data = {
            "id": entity_id,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
            "name": normalized_name,
            "slug": slug,
            "entity_type": entity_type,
            "status": status,
            "external_id": external_id,
            "website": website,
            "registration_number": registration_number,
            "entity_size": entity_size,
            "notes": notes,
            "default_address_id": addresses[0]['id'],
            "parent_id": selected_parent['id'] if selected_parent else None,
            "industry_id": industry.id if industry else None,
            "created_by_id": user.id,
            "updated_by_id": user.id,
            "lft": 1,
            "rght": 2,
            "tree_id": entity_id,
            "level": 0 if not selected_parent else 1
        }

        return {
            "entity": entity_data,
            "address": addresses,
            "contact": contacts,
            "tax_profile": tax_profiles,
            "fincore_entity_mapping": entity_mapping
        }

    def handle(self, *args, **options):
        start_time = time.time()

       # Get user for audit fields
        Employee = get_user_model()
        try:
            user = Employee.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using employee: {user.username} (ID: {user.id}) ({time.time() - start_time:.2f}s)"))
            logger.info(f"Using emoloyee: {user.username}")
        except Employee.DoesNotExist:
            error_msg = f"Employee with id=1 not found. Please ensure user exists. ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        if options['fixed'] and options['random']:
            self.stderr.write(self.style.ERROR("Cannot use --fixed and --random together"))
            logger.error("Invalid arguments: --fixed and --random cannot be used together")
            return

        stats = {'created': 0, 'skipped': [], 'total': 0}
        generated_names = set()
        counters = {
            'entity': Entity.objects.filter(is_active=True).aggregate(Max('id'))['id__max'] or 0,
            'address': Address.objects.filter(is_active=True).aggregate(Max('id'))['id__max'] or 0,
            'contact': Contact.objects.filter(is_active=True).aggregate(Max('id'))['id__max'] or 0,
            'tax': TaxProfile.objects.filter(is_active=True).aggregate(Max('id'))['id__max'] or 0,
            'mapping': FincoreEntityMapping.objects.filter(is_active=True).aggregate(Max('id'))['id__max'] or 0
        }

        self.stdout.write(f"Starting generation... ({time.time() - start_time:.2f}s)")
        logger.info("Starting entity and fincore data generation")

        env_data = load_env_paths(env_var='ENTITIES_JSON', require_exists=False)
        entities_path = env_data.get('ENTITIES_JSON')
        if not entities_path:
            self.stderr.write(self.style.ERROR("ENTITIES_JSON not defined in .env"))
            logger.error("ENTITIES_JSON not defined")
            return

        entity_types = [choice[0] for choice in ENTITY_TYPE_CHOICES]
        statuses = [choice[0] for choice in ENTITY_STATUS_CHOICES]
        company_sizes = ['1-10 employees', '11-50 employees', '51-200 employees', '201-500 employees', '501+ employees']
        address_types = [choice[0] for choice in ADDRESS_TYPE_CHOICES]
        contact_roles = [choice[0] for choice in CONTACT_ROLE_CHOICES]
        tax_identifier_types = [choice[0] for choice in TAX_IDENTIFIER_TYPE_CHOICES]
        legal_statuses = {
            'INDIVIDUAL': ['Sole Proprietor'],
            'BUSINESS': ['LLC', 'Corporation', 'Partnership'],
            'GOVERNMENT': ['Government Agency'],
            'NONPROFIT': ['Non-Profit Organization'],
            'PARTNERSHIP': ['General Partnership', 'Limited Partnership'],
            'SOLE_PROPRIETORSHIP': ['Sole Proprietor']
        }

        name_generator = CompanyNameGenerator()

        if options['all']:
            countries = CustomCountry.objects.filter(is_active=True)
            if not countries.exists():
                self.stderr.write(self.style.ERROR("No countries found in database"))
                logger.error("No countries found in database")
                return
        else:
            country_code = self.get_country_code(options['country'])
            if not country_code:
                self.stderr.write(self.style.ERROR(f"Invalid country: {options['country']}"))
                logger.error(f"Invalid country input: {options['country']}")
                return
            countries = CustomCountry.objects.filter(country_code=country_code, is_active=True)

        for country in countries:
            country_code = country.country_code
            try:
                fake = Faker(f'en_{country_code}')
            except (ValueError, AttributeError):
                fake = Faker()
                logger.warning(f"Locale 'en_{country_code}' not supported, using 'en_US'")

            regions = CustomRegion.objects.filter(country=country, is_active=True)
            cities = CustomCity.objects.filter(subregion__region__country=country, is_active=True)
            industries = Industry.objects.filter(is_active=True)

            if not regions.exists() or not cities.exists() or not industries.exists():
                self.stderr.write(self.style.ERROR(f"No regions, cities, or industries found for {country.name}"))
                logger.error(f"No regions, cities, or industries found for {country.name}")
                stats['skipped'].append({'country': country.name, 'reason': 'No regions, cities, or industries'})
                continue

            if options['fixed']:
                num_entities = options['count']
                base_distribution = {
                    'ACTIVE': 70,
                    'ON_HOLD': 10,
                    'PENDING': 5,
                    'SUSPENDED': 10,
                    'INACTIVE': 5
                }
                status_distribution = ratio_distribution(base_distribution, num_entities)
                available_statuses = []
                for status, count in status_distribution.items():
                    available_statuses.extend([status] * count)
                random.shuffle(available_statuses)
            elif options['count']:
                num_entities = options['count']
                available_statuses = statuses
            elif options['max']:
                num_entities = random.randint(1, options['max'])
                available_statuses = statuses
            else:
                num_entities = random.randint(options['min'], options['max'] or 10)
                available_statuses = statuses

            logger.info(f"Generating {num_entities} entities for {country.name}")
            potential_parents = []
            entity_counter = 0
            generated_entities = []
            while entity_counter < num_entities:
                stats['total'] += 1
                try:
                    status = available_statuses[entity_counter] if options['fixed'] and entity_counter < len(available_statuses) else random.choice(available_statuses)
                    parent_entity = None if entity_counter == 0 else None
                    entity_data = self.generate_entity(
                        fake, name_generator, country, country_code, regions, cities, industries,
                        entity_types, [status], company_sizes, address_types, contact_roles, tax_identifier_types,
                        legal_statuses, generated_names, parent_entity, counters, user, is_fixed=options['fixed'], generated_entities=generated_entities,
                        potential_parents=potential_parents
                    )
                    if entity_data is None:
                        stats['skipped'].append({'entity': f"Entity {entity_counter + 1} in {country.name}", 'reason': 'Invalid address or tax profile'})
                        logger.warning(f"Skipping entity {entity_counter + 1} in {country.name}: Invalid address or tax profile")
                        continue
                    json_data = {
                        'entity': [entity_data['entity']],
                        'address': entity_data['address'],
                        'contact': entity_data['contact'],
                        'tax_profile': entity_data['tax_profile'],
                        'fincore_entity_mapping': [entity_data['fincore_entity_mapping']]
                    }
                    entity_slug = entity_data['entity']['slug']
                    entity_name = entity_data['entity']['name'].lower().replace(' ', '_')
                    entities_json = str(Path(entities_path) / country_code / f"{entity_name}.json")
                    self.stdout.write(f"Generating entity data for: {entity_data['entity']['name']} ({entity_slug}) in {country_code}")
                    logger.info(f"Generating entity data for {entity_data['entity']['name']} in {country_code}")

                    try:
                        Path(entities_json).parent.mkdir(parents=True, exist_ok=True)
                        with open(entities_json, 'w', encoding='utf-8') as f:
                            json.dump(json_data, f, indent=4, ensure_ascii=False)
                        self.stdout.write(self.style.SUCCESS(f"Generated JSON at {entities_json}"))
                        logger.info(f"Generated JSON at {entities_json}")
                        stats['created'] += 1
                        entity_counter += 1
                        generated_entities.append(entity_data['entity'])
                        if entity_data['entity']['entity_type'] in ('BUSINESS', 'GOVERNMENT', 'NONPROFIT', 'PARTNERSHIP'):
                            potential_parents.append(entity_data['entity'])
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"Error writing JSON for {entity_slug} in {country_code}: {str(e)}"))
                        logger.error(f"Error writing JSON for {entity_slug} in {country_code}: {str(e)}")
                        stats['skipped'].append({'entity': f"Entity {entity_data['entity']['name']}", 'reason': str(e)})
                        continue
                except Exception as e:
                    stats['skipped'].append({'entity': f"Entity {entity_counter + 1} in {country.name}", 'reason': str(e)})
                    logger.warning(f"Skipping entity generation {entity_counter + 1} in {country.name}: {str(e)}")
                    if options['fixed']:
                        entity_counter += 1

        self.stdout.write(self.style.SUCCESS(f"Generation Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f"  - Total entities: {stats['total']}")
        self.stdout.write(f"  - Created: {stats['created']}")
        self.stdout.write(f"  - Skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f"    - {skipped.get('country', skipped.get('entity'))}: {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f"    - ... and {len(stats['skipped']) - 5} more skipped")
        self.stdout.write(self.style.SUCCESS(f"Generation Completed in {time.time() - start_time:.2f}s"))
        logger.info(f"Generation Summary: Total={stats['total']}, Created={stats['created']}, Skipped={len(stats['skipped'])}")
