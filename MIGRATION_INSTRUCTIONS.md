# Fix: Add category column to measurement_entries table

## Error
```
column measurement_entries.category does not exist
```

## Solution

The `measurement_entries` table is missing the `category` column that is defined in the model.

### Option 1: Run SQL Migration (Recommended)

Connect to your PostgreSQL database and run:

```sql
ALTER TABLE measurement_entries ADD COLUMN category VARCHAR;
```

Or use the provided SQL file:
```bash
psql -U your_username -d your_database -f migrate_add_category.sql
```

### Option 2: Run Python Migration Script

1. Activate your virtual environment:
   ```bash
   cd backend
   .\venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

2. Run the migration script:
   ```bash
   python add_category_column.py
   ```

### Option 3: Recreate Database (Development Only)

If you're in development and can lose data:

```bash
cd backend
python init_db.py
```

This will recreate all tables with the correct schema.
