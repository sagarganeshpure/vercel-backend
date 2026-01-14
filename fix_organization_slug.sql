-- Fix organization_slug column in users table
-- For PostgreSQL databases

-- Step 1: Make the column nullable (if it's NOT NULL)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'organization_slug'
        AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL;
        RAISE NOTICE 'Made organization_slug column nullable';
    END IF;
END $$;

-- Step 2: Remove the column
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





