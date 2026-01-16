import json

from django.core.serializers.json import DjangoJSONEncoder

from industries.models import Industry


def dump_industry_data(output_file='../industries.json'):
    """
    Dumps all active Industry records to a JSON file with hierarchical structure.

    Args:
        output_file (str): Path to the output JSON file.

    """
    try:
        # Fetch all active industries
        industries = Industry.objects.all()

        # Prepare data structure for JSON
        def serialize_industry(industry):
            return {
                'id': industry.id,
                'code': industry.code,
                'description': industry.description,
                'level': industry.level,
                'sector': industry.sector,
                'parent_id': industry.parent_id,
                'created_at': industry.created_at,
                'updated_at': industry.updated_at,
                'is_active': industry.is_active,
                'deleted_at': industry.deleted_at,
                'created_by_id': industry.created_by_id,
                'updated_by_id': industry.updated_by_id,
                'deleted_by_id': industry.deleted_by_id,
                'children': [
                    serialize_industry(child)
                    for child in industry.children.filter(is_active=True)
                ]
            }

        # Serialize all industries
        data = [serialize_industry(industry) for industry in industries if industry.parent is None]

        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=DjangoJSONEncoder, indent=2, ensure_ascii=False)

        print(f"Successfully dumped {len(data)} top-level industries to {output_file}")

    except Exception as e:
        print(f"Error dumping industry data: {str(e)}")
        raise

if __name__ == '__main__':
    dump_industry_data()
