import json
import os

import psycopg2
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from psycopg2 import sql


class Command(BaseCommand):
    help = 'Displays record count and column names for specified tables in the database'

    def handle(self, *args, **options):
        # Load environment variables from .env file
        load_dotenv()

        # Database connection parameters from .env
        db_params = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT')
        }

        # List of tables from the schema
        tables = [
            'address', 'billing_schedule', 'contact', 'entity', 'fincore_entity_mapping',
            'gst_configuration', 'industries_industry', 'invoice', 'line_item',
            'locations_customcity', 'locations_customcountry', 'locations_customcountry_global_regions',
            'locations_customregion', 'locations_customsubregion', 'locations_globalregion',
            'locations_location', 'locations_timezone', 'payment', 'payment_method',
            'status', 'tax_profile', 'users_address', 'users_user'
        ]

        # Dictionary to hold the final JSON data
        table_data = {}
        table_data_min = {}

        try:
            # Connect to the database
            conn = psycopg2.connect(**db_params)
            cursor = conn.cursor()

            # Iterate through each table
            for table in tables:
                # Get column names
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                """, (table,))
                columns = [row[0] for row in cursor.fetchall()]

                # Get record count
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                record_count = cursor.fetchone()[0]

                # Add data to the dictionary
                table_data[table] = {
                    "record_count": record_count,
                    "columns": columns
                }

                # Add data to the dictionary
                table_data_min[table] = {
                    "record_count": record_count,
                }

                # Output results in text format
                # self.stdout.write(f"\nTable: {table}")
                # self.stdout.write(f"Record Count: {record_count}")
                # self.stdout.write(f"Columns: {', '.join(columns)}")

        except Exception as e:
            self.stderr.write(f"Error: {e}")

        finally:
            # Close the connection
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        # Combine both JSON outputs
        tables_json = {
            "all_info": table_data,
            "concise_info": table_data_min
        }

        # Output the final JSON data
        self.stdout.write(json.dumps(tables_json, indent=4))

