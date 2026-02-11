########################################################################################################################

########################################################################################################################

import logging

from django.db import transaction
from django.db.models.functions import Length
from teamcentral.models import Department, EmployeeType, EmploymentStatus, LeaveType, MemberStatus, Role

logger = logging.getLogger(__name__)

# List of models with a 'code' field
models_with_code = [
    ('EmploymentStatus', EmploymentStatus),
    ('Role', Role),
    ('LeaveType', LeaveType),
    ('EmployeeType', EmployeeType),
    ('MemberStatus', MemberStatus),
    ('Department', Department),
]

def truncate_code(code, model, max_length=4):
    """Truncate code to max_length, ensuring uniqueness for the given model."""
    base_code = code[:max_length]
    counter = 1
    new_code = base_code
    while model.all_objects.filter(code=new_code).exists():
        # If truncated code exists, append a number
        suffix = str(counter)
        new_code = f"{base_code[:max_length-len(suffix)]}{suffix}"
        counter += 1
        if counter > 9999:  # Prevent infinite loop
            raise ValueError(f"Cannot generate unique code for {base_code} in {model.__name__}")
    return new_code

@transaction.atomic
def update_long_codes_all_models():
    """Update codes with length > 4 to max 4 characters across all models."""
    updated_counts = {}
    for model_name, model in models_with_code:
        long_codes = model.objects.annotate(code_length=Length('code')).filter(code_length__gt=4)
        updated_count = 0
        for record in long_codes:
            old_code = record.code
            new_code = truncate_code(old_code, model)
            record.code = new_code
            record.save()
            logger.info(f"Updated {model_name} code from {old_code} to {new_code}")
            updated_count += 1
        updated_counts[model_name] = updated_count
        logger.info(f"Updated {updated_count} {model_name} records")
    return updated_counts

# Execute the update
updated = update_long_codes_all_models()
for model_name, count in updated.items():
    print(f"Updated {count} {model_name} records")

########################################################################################################################

# from users.models import Employee, Member, SignUpRequest
# from users.services.member import MemberService
# from django.utils import timezone
# from datetime import timedelta

# # Get the user
# employee = Employee.objects.get(email='shekharsvbhosale@gmail.com')
# member = Member.objects.get(employee=employee)

# # Delete any existing SignUpRequest to avoid duplicates
# SignUpRequest.objects.filter(user=employee).delete()

# # Create a new SignUpRequest
# signup_request = SignUpRequest(
#     user=employee,
#     sso_provider=employee.sso_provider or 'GOOGLE',
#     sso_id=employee.sso_id,
#     expires_at=timezone.now() + timedelta(days=7),
#     created_by=employee,
# )
# signup_request.save(user=employee)

# # Send verification email
# MemberService.send_verification_email(member)

########################################################################################################################

# from locations.models import CustomRegion
# from locations.models import CustomSubRegion
# from django.db import transaction
# import re

# with transaction.atomic():
#     unknown_regions = CustomRegion.objects.filter(name__icontains='District')
#     unknown_subregions = CustomSubRegion.objects.filter(name__icontains='District')
#     subregion_count = 0
#     region_count = 0

#     for subregion in unknown_subregions:
#         original_name = subregion.name
#         cleaned_name = re.sub(r'\s*District\s*', ' ', original_name, flags=re.IGNORECASE).strip()
#         cleaned_name = re.sub(r'\s+', ' ', cleaned_name)

#         if cleaned_name != original_name:
#             subregion.name = cleaned_name
#             subregion.save(update_fields=["name"])
#             updated_count += 1

#     for region in unknown_regions:
#         original_name = region.name
#         cleaned_name = re.sub(r'\s*District\s*', ' ', original_name, flags=re.IGNORECASE).strip()
#         cleaned_name = re.sub(r'\s+', ' ', cleaned_name)

#         if cleaned_name != original_name:
#             region.name = cleaned_name
#             region.save(update_fields=["name"])
#             region_count += 1

# print(f"Successfully updated {region_count} regions.")
# print(f"Successfully updated {subregion_count} subregions.")


########################################################################################################################

# '''Find skipped records'''
# import json
# from pathlib import Path
# import unicodedata


# def normalize_text(label):
#         """Normalize text by removing diacritics."""
#         if not label:
#             return label
#         normalized = ''.join(c for c in unicodedata.normalize('NFD', label) if unicodedata.category(c) != 'Mn')
#         return normalized.strip()

# json_filename = "/Users/redstar/pyc/common_data/geonames/cities/NZ.json"
# with open(json_filename, 'r', encoding='utf-8') as f:
#     data = json.load(f)

# country_code = "NZ"
# skipped_reasons = {
#     'missing_name': 0,
#     'country_code_mismatch': 0,
#     'missing_admin1_code': 0,
#     'invalid_feature_code': 0,
#     'missing_admin2_code': 0
# }
# valid_feature_codes = ['PPL', 'PPLA', 'PPLC', 'PPLG']

# for index, record in enumerate(data):
#     error_reason = None
#     if not record.get('name') or not normalize_text(record.get('name')):
#         error_reason = 'Missing name'
#         skipped_reasons['missing_name'] += 1
#     elif record.get('country_code', '').upper() != country_code.upper():
#         error_reason = f"Country code mismatch: expected {country_code}, got {record.get('country_code')}"
#         skipped_reasons['country_code_mismatch'] += 1
#     elif not record.get('admin1_code'):
#         error_reason = 'Missing admin1_code'
#         skipped_reasons['missing_admin1_code'] += 1
#     elif record.get('feature_code') and record.get('feature_code') not in valid_feature_codes:
#         error_reason = 'Invalid feature_code'
#         skipped_reasons['invalid_feature_code'] += 1
#     elif not record.get('admin2_code'):
#         error_reason = 'Missing admin2_code'
#         skipped_reasons['missing_admin2_code'] += 1

#     if error_reason:
#         print(f"Record {index}: {record.get('name', 'N/A')} - Skipped: {error_reason}")

# print("Summary of skipped reasons:")
# for reason, count in skipped_reasons.items():
#     print(f"{reason}: {count}")


# ########################################################################################################################

# import json
# from pathlib import Path

# json_filename = Path(env_data.get('CITIES_JSON')) / f"{country_code}.json"
# with open(json_filename, 'r', encoding='utf-8') as f:
#     data = json.load(f)

# region_names = {}
# for record in data:
#     name = record.get('admin1_name') or f"Region {record.get('admin1_code')}"
#     country_code = record.get('country_code')
#     key = (country_code, normalize_text(name).lower())
#     region_names[key] = region_names.get(key, 0) + 1

# duplicates = {k: v for k, v in region_names.items() if v > 1}
# if duplicates:
#     print(f"Found duplicate regions in {json_filename}: {duplicates}")
# else:
#     print(f"No duplicate regions found in {json_filename}")


# ########################################################################################################################

# import random
# import re
# from typing import List, Optional, Dict

# class CompanyNameGenerator:
#     """A comprehensive library for generating corporate company names with various patterns and styles."""

#     def __init__(self, seed: Optional[int] = None):
#         """Initialize the company name generator with optional random seed."""
#         if seed is not None:
#             random.seed(seed)

#         self.prefixes = [
#             'Quantum', 'Nexus', 'Apex', 'Vertex', 'Synergy', 'Innovate', 'Core',
#             'Dynamic', 'Global', 'Prime', 'NextGen', 'Fusion', 'Strive', 'Evolve',
#             'Pinnacle', 'Vanguard', 'Optima', 'Zentrix', 'Neo', 'Proton', 'Alpha',
#             'Omega', 'Nova', 'Stellar', 'Horizon', 'Vital', 'Zenith', 'Eclipse'
#         ]

#         self.bases = [
#             'Tech', 'Systems', 'Solutions', 'Group', 'Partners', 'Ventures',
#             'Innovations', 'Enterprises', 'Technologies', 'Dynamics', 'Labs',
#             'Consulting', 'Analytics', 'Networks', 'Holdings', 'Associates',
#             'Collective', 'Alliance', 'Syndicate', 'Consortium', 'Works', 'Hub'
#         ]

#         self.suffixes = [
#             'Inc', 'LLC', 'Corp', 'Co', 'Limited', 'Solutions', 'Group',
#             'International', 'Technologies', 'Systems', 'Partners', 'Global',
#             'Worldwide', 'Enterprises', 'Ventures', 'Associates'
#         ]

#         self.industries = {
#             'tech': ['Software', 'AI', 'Cloud', 'Data', 'Cyber', 'Quantum', 'Robotics', 'Blockchain'],
#             'finance': ['Capital', 'Wealth', 'Invest', 'Financial', 'Trust', 'Equity', 'Banking'],
#             'healthcare': ['Bio', 'Med', 'Health', 'Care', 'Pharma', 'Genix', 'Vital'],
#             'energy': ['Energy', 'Solar', 'Power', 'Green', 'Renewable', 'Eco', 'Volt'],
#             'manufacturing': ['Industries', 'Works', 'Forge', 'Fabrication', 'Production'],
#             'consulting': ['Consulting', 'Advisory', 'Strategy', 'Insights', 'Vision'],
#             'media': ['Media', 'Digital', 'Stream', 'Content', 'Broadcast']
#         }

#         self.descriptors = [
#             'Advanced', 'Integrated', 'Strategic', 'Premier', 'Elite', 'Smart',
#             'Future', 'Innovative', 'CuttingEdge', 'Progressive', 'Dynamic'
#         ]

#     def generate_name(self, format_type: str = 'standard', industry: Optional[str] = None,
#                      include_descriptor: bool = False, acronym: bool = False) -> str:
#         """
#         Generate a company name based on specified parameters.

#         Args:
#             format_type (str): Type of name format ('standard', 'short', 'complex', 'modern')
#             industry (str, optional): Industry for specific naming (e.g., 'tech', 'finance')
#             include_descriptor (bool): Whether to include a descriptor like 'Advanced'
#             acronym (bool): Whether to generate an acronym-based name

#         Returns:
#             str: Generated company name

#         Raises:
#             ValueError: If invalid format_type or industry is provided
#         """
#         valid_formats = ['standard', 'short', 'complex', 'modern']
#         if format_type not in valid_formats:
#             raise ValueError(f"Invalid format_type. Must be one of {valid_formats}")

#         if industry and industry not in self.industries:
#             raise ValueError(f"Invalid industry. Must be one of {list(self.industries.keys())}")

#         if acronym:
#             return self._generate_acronym_name(industry)

#         name_parts = []

#         if include_descriptor:
#             name_parts.append(random.choice(self.descriptors))

#         if format_type == 'standard':
#             name_parts.append(random.choice(self.prefixes))
#             name_parts.append(random.choice(self.bases))
#             name_parts.append(random.choice(self.suffixes))

#         elif format_type == 'short':
#             name_parts.append(random.choice(self.prefixes))
#             name_parts.append(random.choice(self.suffixes))

#         elif format_type == 'complex':
#             name_parts.append(random.choice(self.prefixes))
#             name_parts.append(random.choice(self.bases))
#             if industry:
#                 name_parts.append(random.choice(self.industries[industry]))
#             name_parts.append(random.choice(self.suffixes))

#         elif format_type == 'modern':
#             name_parts.append(self._create_modern_prefix())
#             if random.random() < 0.5:
#                 name_parts.append(random.choice(self.bases))
#             if industry:
#                 name_parts.append(random.choice(self.industries[industry]))

#         return ''.join(name_parts).replace(' ', '')

#     def _generate_acronym_name(self, industry: Optional[str] = None) -> str:
#         """Generate an acronym-style company name."""
#         words = random.sample(self.prefixes + self.bases, 3)
#         if industry:
#             words[1] = random.choice(self.industries[industry])

#         acronym = ''.join(word[0].upper() for word in words)
#         suffix = random.choice(self.suffixes)
#         return f"{acronym}{suffix}"

#     def _create_modern_prefix(self) -> str:
#         """Create a modern-style prefix by combining partial words."""
#         word1 = random.choice(self.prefixes)
#         word2 = random.choice(self.prefixes)
#         return word1[:len(word1)//2] + word2[len(word2)//2:]

#     def generate_multiple_names(self, count: int, **kwargs) -> List[str]:
#         """
#         Generate multiple company names.

#         Args:
#             count (int): Number of names to generate
#             **kwargs: Parameters to pass to generate_name

#         Returns:
#             List[str]: List of generated company names
#         """
#         if count < 1:
#             raise ValueError("Count must be positive")

#         return [self.generate_name(**kwargs) for _ in range(count)]

#     def customize_vocabulary(self, category: str, words: List[str]) -> None:
#         """
#         Customize the vocabulary for a specific category.

#         Args:
#             category (str): Category to update ('prefixes', 'bases', 'suffixes', 'descriptors')
#             words (List[str]): New words to add to the category

#         Raises:
#             ValueError: If invalid category is provided
#         """
#         valid_categories = ['prefixes', 'bases', 'suffixes', 'descriptors']
#         if category not in valid_categories:
#             raise ValueError(f"Invalid category. Must be one of {valid_categories}")

#         setattr(self, category, list(set(getattr(self, category) + words)))

#     def add_industry(self, industry: str, terms: List[str]) -> None:
#         """
#         Add a new industry with specific terms.

#         Args:
#             industry (str): Industry name
#             terms (List[str]): Industry-specific terms
#         """
#         if not re.match(r'^[a-zA-Z]+$', industry):
#             raise ValueError("Industry name must contain only letters")

#         self.industries[industry] = terms

#     def get_available_industries(self) -> List[str]:
#         """Return list of available industries."""
#         return list(self.industries.keys())


# if __name__ == "__main__":
#     # Example usage
#     generator = CompanyNameGenerator(seed=42)

#     # Generate different types of names
#     print("Standard name:", generator.generate_name())
#     print("Short name:", generator.generate_name(format_type='short'))
#     print("Tech industry name:", generator.generate_name(format_type='complex', industry='tech'))
#     print("Modern name with descriptor:", generator.generate_name(format_type='modern', include_descriptor=True))
#     print("Acronym name:", generator.generate_name(acronym=True))

#     # Generate multiple names
#     print("\nMultiple names:")
#     names = generator.generate_multiple_names(3, format_type='standard', include_descriptor=True)
#     for name in names:
#         print(name)

#     # Add custom industry
#     generator.add_industry('space', ['Aero', 'Orbit', 'Star', 'Galactic'])
#     print("\nSpace industry name:", generator.generate_name(industry='space'))

#     # Customize vocabulary
#     generator.customize_vocabulary('prefixes', ['Astro', 'Cosmo'])
#     print("Name with custom prefix:", generator.generate_name())


# ########################################################################################################################
