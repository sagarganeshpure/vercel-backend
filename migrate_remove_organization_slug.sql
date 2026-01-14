-- Migration script to remove organization_slug column from users table
-- For PostgreSQL databases

-- Check if column exists and remove it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'organization_slug'
    ) THEN
        ALTER TABLE users DROP COLUMN organization_slug;
        RAISE NOTICE 'Column organization_slug removed from users table';
    ELSE
        RAISE NOTICE 'Column organization_slug does not exist. Nothing to remove.';
    END IF;
END $$;
