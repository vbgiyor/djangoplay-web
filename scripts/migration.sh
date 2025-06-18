#!/bin/bash

# Set the path to the backend directory (where manage.py is)
BACKEND_DIR=$(dirname "$(realpath "$0")")/../backend

# Check if enough arguments are provided and they are even-numbered
if [ $# -lt 2 ] || [ $(( $# % 2 )) -ne 0 ]; then
  echo "Usage: $0 <source1> <dest1> <source2> <dest2> ... <sourceN> <destN>"
  exit 1
fi

# Check if manage.py exists
if [[ ! -f "$BACKEND_DIR/manage.py" ]]; then
  echo "Error: manage.py not found in $BACKEND_DIR"
  exit 1
fi

# Remove the SQLite database and all migration files
echo "Removing existing database and migration files..."
rm -f "$BACKEND_DIR/db.sqlite3"
find "$BACKEND_DIR" -path "*/migrations/*.py" -not -name "__init__.py" -delete
find "$BACKEND_DIR" -path "*/migrations/*.pyc" -delete

sleep 1

# List of apps to make migrations for
apps=("core" "users" "locations" "clients" "invoices")

# Create migrations for each app
echo "Creating migrations for apps..."
for app in "${apps[@]}"; do
    python3 "$BACKEND_DIR/manage.py" makemigrations "$app" || {
        echo "Failed to create migrations for $app"
        exit 1
    }
done

# Apply migrations for each app
echo "Applying migrations for apps..."
for app in "${apps[@]}"; do
    python3 "$BACKEND_DIR/manage.py" migrate "$app" || {
        echo "Failed to apply migrations for $app"
        exit 1
    }
done

# Apply all migrations (in case there are additional apps or migration steps)
echo "Applying all migrations..."
python3 "$BACKEND_DIR/manage.py" migrate || {
    echo "Failed to apply all migrations"
    exit 1
}

sleep 1

# Create empty migrations for data population and store their paths
echo "Creating empty migrations for data population..."
migration_files=""
for app in "users" "locations" "clients" "invoices"; do
    migration_name="populate_${app}"
    python3 "$BACKEND_DIR/manage.py" makemigrations --empty "$app" --name "$migration_name" || {
        echo "Failed to create empty migration for $app"
        exit 1
    }
    # Find the latest migration file for the app
    migration_file=$(find "$BACKEND_DIR/$app/migrations" -type f -name "*_${migration_name}.py" -print -quit)
    if [[ -z "$migration_file" ]]; then
        echo "Error: Migration file for $app ($migration_name) was not created."
        exit 1
    fi
    migration_files="$migration_files $app:$migration_file"
    echo "Created migration file for $app: $migration_file"
done

sleep 1

# Loop through the arguments and copy files
echo "Copying source files to destination migration files..."
while [ $# -gt 0 ]; do
  source_file="$1"
  dest_file="$2"
  
  # Check if the source file exists
  if [[ ! -f "$source_file" ]]; then
    echo "Error: Source file '$source_file' does not exist."
    exit 1
  fi
  
  # Ensure destination file's directory exists
  dest_dir=$(dirname "$dest_file")
  if [[ ! -d "$dest_dir" ]]; then
    echo "Error: Destination directory '$dest_dir' does not exist."
    exit 1
  fi
  
  # Check if destination file exists
  if [[ -f "$dest_file" ]]; then
    # Copy the content from the source file to the destination
    cp "$source_file" "$dest_file" || {
        echo "Failed to copy $source_file to $dest_file"
        exit 1
    }
    echo "Successfully copied $source_file to $dest_file"
  else
    echo "Error: Destination migration file '$dest_file' does not exist."
    exit 1
  fi
  
  # Shift to next pair of arguments
  shift 2
done

sleep 2

# Run migrations again with verbosity for better logging
echo "Running final migrations with verbosity..."
for app in "${apps[@]}"; do
    python3 "$BACKEND_DIR/manage.py" migrate "$app" --verbosity 3 || {
        echo "Failed to apply final migrations for $app"
        exit 1
    }
    sleep 3
done

echo "Migration process completed successfully."

# Command to execute:
# ../scripts/migration.sh \
# path-to-data/populate_users.py ~users/migrations/0002_populate_users.py \
# path-to-data/populate_locations.py ~locations/migrations/0002_populate_locations.py \
# path-to-data/populate_clients.py ~clients/migrations/0002_populate_clients.py \
# path-to-data/populate_invoices.py ~invoices/migrations/0002_populate_invoices.py