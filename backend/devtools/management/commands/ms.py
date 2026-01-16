import logging
import subprocess
import time
from threading import Event, Thread

from core.utils.cmd_status import animate_processing
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """
        Run initialization commands and invoice generation for specified countries and iterations.

        Arguments:
        --iterations <int>: Number of iterations for invoice generation loop (required).
        --processes <int>: Number of sequential processes for country tasks (default: 4, max 4).
        --country <str>: Country code for entity and invoice generation (default: IN).
        --count <int>: Number of entities to generate per country (default: 10).
        --skipglobal: Skip global initialization commands if already run (default: False).

        Execution Phases:
        1. Global Initialization (skipped if --skipglobal is specified):
        Runs once for all countries:
        - create_superuser
        - import_system_constants_users
        - import_industries
        - import_global_regions --datasource geonames
        - import_country_info --datasource geonames
        - import_timezones
        - import_status_paymentmethods
        - generate_industry_line_items
        - refresh_redis_cache
        Logs 'Running <command>', 'Failed <command> - <error>'.

        2. Country-Specific Initialization:
        Runs once per country in country_configs:
        - import_cities --datasource geonames --country <country> --batch-size 90000
        - import_postal_codes --country <country> --create-locations -v 3
        - generate_entities --country <country> --count <count> --fixed
        - import_entities --country <country>
        Logs 'Running <command>' and 'Failed <command> - <error>'.

        3. Iterative Commands:
        Runs for each country in country_configs, repeated <iterations> times:
        - generate_entities --country <country> --count <count> --fixed
        - import_entities --country <country>
        - generate_import_gst_configs --all (only if country=IN)
        - generate_import_invoices --all --country <country>
        Logs 'Running <command>' and 'Failed <command> - <error>'.

        4. Final Commands:
        - update_locations_timezones --country <country> (for each country in country_configs)
        - refresh_redis_cache
        Logs 'Running <command>' and 'Failed <command> - <error>'.

        Country Configs:
        - If --country=IN, processes IN, NZ and GB with count=10.
        - If --country is not IN (e.g., NZ), processes only the specified country with --count (default: 10).

        Examples:
        - ./manage.py masterscript --iterations 1 --processes 4
        Runs global initialization, processes IN, NZ and GB, runs iterative commands (including generate_import_gst_configs for IN), runs final commands.
        - ./manage.py masterscript --iterations 1 --processes 4 --country NZ --count 20
        Runs global initialization, processes only NZ with 20 entities, runs iterative commands, runs final commands.
        - ./manage.py masterscript --iterations 1 --processes 4 --skipglobal
        Skips global initialization, processes IN, NZ and GB, runs iterative commands (including generate_import_gst_configs for IN), runs final commands.
        """

    def add_arguments(self, parser):
        parser.add_argument('--iterations', type=int, required=True, help='Number of iterations for invoice generation loop.')
        parser.add_argument('--processes', type=int, default=4, help='Number of sequential processes for country tasks (max 4).')
        parser.add_argument('--country', type=str, default='IN', help='Country code for entity and invoice generation (default: IN).')
        parser.add_argument('--count', type=int, default=10, help='Number of entities to generate per country (default: 10).')
        parser.add_argument('--skipglobal', action='store_true', help='Skip global initialization commands.')

    def run_command(self, command, stdout, retries=1, wait_seconds=1):
        stop_event = Event()
        animation_thread = None
        is_tty = stdout.isatty()
        if is_tty:
            animation_thread = Thread(target=animate_processing, args=(stop_event, stdout))
            animation_thread.start()

        for attempt in range(1, retries + 1):
            start_time = time.time()
            try:
                process = subprocess.run(command, check=True, capture_output=True, text=True)
                if process.stdout:
                    logger.info(f"Command {' '.join(command)} output: {process.stdout}")
                stop_event.set()
                if animation_thread:
                    animation_thread.join()
                return True, ""
            except subprocess.CalledProcessError as e:
                error_msg = f"Attempt {attempt} failed: {e.stderr}"
                logger.error(f"Command {' '.join(command)} failed: {error_msg}, Return code: {e.returncode}")
                stop_event.set()
                if animation_thread:
                    animation_thread.join()
                if attempt < retries:
                    time.sleep(wait_seconds)
                else:
                    stdout.write(self.style.ERROR(f"Failed: {' '.join(command)} - {e.stderr}"))
                    return False, e.stderr
            finally:
                if not stop_event.is_set() and time.time() - start_time >= 2:
                    stop_event.set()
                    if animation_thread:
                        animation_thread.join()
        stdout.write(self.style.ERROR(f"Failed: {' '.join(command)} - Unknown error"))
        return False, "Unknown error"

    def run_country_commands(self, args, stdout):
        country, eicount, iteration = args
        logger.info(f"Starting run_country_commands for {country}, iteration {iteration}")
        commands = [
            ['python', 'manage.py', 'generate_entities', '--country', country, '--count', str(eicount), '--fixed'],
            ['python', 'manage.py', 'import_entities', '--country', country],
        ]
        if country == 'IN':
            commands.append(['python', 'manage.py', 'generate_import_gst_configs', '--all'])
        commands.append(['python', 'manage.py', 'generate_import_invoices', '--all', '--country', country])

        results = []
        for cmd in commands:
            stdout.write(self.style.NOTICE(f"Running {' '.join(cmd)}"))
            if cmd[2] == 'generate_import_invoices':
                logger.info(f"Iteration {iteration}: Starting invoice generation for {country}")
            success, err = self.run_command(cmd, stdout)
            if cmd[2] == 'generate_import_invoices':
                logger.info(f"Iteration {iteration}: Completed invoice generation for {country}")
            if not success:
                results.append({'command': ' '.join(cmd), 'error': err})
        return country, iteration, results

    def handle(self, *args, **options):
        self.stdout._out = open(self.stdout._out.fileno(), 'w', buffering=1)
        iterations = options['iterations']
        processes = min(options['processes'], 4)
        country = options['country']
        count = options['count']
        skipglobal = options['skipglobal']
        if iterations <= 0:
            raise CommandError('--iterations must be a positive integer')

        failed_commands = []

        # Set country_configs based on input
        if country != 'IN':
            country_configs = [(country, count)]
        else:
            # Default for IN, process IN, NZ and GB
            country_configs = [('IN', 10), ('NZ', 10), ('GB', 10), ('KR', 10), ('FR', 10), ('JP', 10), ('MY', 10)]

        # Global initialization commands (run once for all unless skipped)
        init_commands = [
            ['python', 'manage.py', 'create_superuser'],
            ['python', 'manage.py', 'import_system_constants_users'],
            ['python', 'manage.py', 'import_industries'],
            ['python', 'manage.py', 'import_global_regions', '--datasource', 'geonames'],
            ['python', 'manage.py', 'import_country_info', '--datasource', 'geonames'],
            ['python', 'manage.py', 'import_timezones'],
            ['python', 'manage.py', 'import_status_paymentmethods'],
            ['python', 'manage.py', 'generate_industry_line_items'],
            ['python', 'manage.py', 'refresh_redis_cache'],
        ]

        if skipglobal:
            self.stdout.write(self.style.WARNING("Skipped global initialization commands - --skipglobal specified"))
        else:
            self.stdout.write(self.style.SUCCESS('Starting global initialization commands...'))
            for cmd in init_commands:
                self.stdout.write(self.style.NOTICE(f"Running {' '.join(cmd)}"))
                success, err = self.run_command(cmd, self.stdout)
                if not success:
                    failed_commands.append({'command': ' '.join(cmd), 'error': err})
                if cmd[2] in ['generate_industry_line_items', 'refresh_redis_cache']:
                    time.sleep(2)

        # Country-specific initialization commands (run once per country in country_configs)
        for c, eicount in country_configs:
            self.stdout.write(self.style.SUCCESS(f'Starting country-specific initialization for {c}...'))
            country_init_commands = [
                ['python', 'manage.py', 'import_cities', '--datasource', 'geonames', '--country', c, '--batch-size', '90000'],
                ['python', 'manage.py', 'import_postal_codes', '--country', c, '--create-locations', '-v', '3'],
                ['python', 'manage.py', 'generate_entities', '--country', c, '--count', str(eicount), '--fixed'],
                ['python', 'manage.py', 'import_entities', '--country', c],
            ]
            for cmd in country_init_commands:
                self.stdout.write(self.style.NOTICE(f"Running {' '.join(cmd)}"))
                success, err = self.run_command(cmd, self.stdout)
                if not success:
                    failed_commands.append({'command': ' '.join(cmd), 'error': err})

        # Iterative commands
        self.stdout.write(self.style.SUCCESS(f'Starting Iteration: {iterations} with {processes} processes...'))
        for i in range(iterations):
            self.stdout.write(self.style.NOTICE(f'\n--- Iteration {i+1} of {iterations} ---'))
            results = []
            for c, eicount in country_configs:
                result = self.run_country_commands((c, eicount, i+1), self.stdout)
                results.append(result)
            for country, iteration, errors in results:
                if errors:
                    failed_commands.append({'iteration': iteration, 'country': country, 'errors': errors})

        # Final commands
        self.stdout.write(self.style.SUCCESS('Starting final commands...'))
        # Run update_locations_timezones for each country
        for c, _ in country_configs:
            cmd = ['python', 'manage.py', 'update_locations_timezones', '--country', c]
            self.stdout.write(self.style.NOTICE(f"Running {' '.join(cmd)}"))
            success, err = self.run_command(cmd, self.stdout)
            if success:
                # Check if the command processed any cities by looking for "Cities updated: X" in output
                process = subprocess.run(cmd, check=True, capture_output=True, text=True)
                if "Cities updated: 0" in process.stdout:
                    logger.warning(f"Command {' '.join(cmd)} executed but updated no cities")
                    failed_commands.append({'command': ' '.join(cmd), 'error': 'No cities updated'})
                else:
                    logger.info(f"Command {' '.join(cmd)} executed successfully")
            else:
                failed_commands.append({'command': ' '.join(cmd), 'error': err})

        # Run final refresh_redis_cache
        self.stdout.write(self.style.NOTICE("Running python manage.py refresh_redis_cache"))
        try:
            subprocess.run(['python', 'manage.py', 'refresh_redis_cache'], check=True)
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"Failed: python manage.py refresh_redis_cache - {e.stderr}"))
            failed_commands.append({'command': 'python manage.py refresh_redis_cache', 'error': e.stderr})

        if failed_commands:
            self.stdout.write(self.style.ERROR('Summary of Failures:'))
            for fail in failed_commands:
                if 'iteration' in fail:
                    for error in fail['errors']:
                        self.stdout.write(self.style.ERROR(
                            f"Iteration {fail['iteration']} ({fail['country']}): {error['command']} - {error['error']}"
                        ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f"Command: {fail['command']} - {fail['error']}"
                    ))
        else:
            self.stdout.write(self.style.SUCCESS('All commands ran successfully.'))
