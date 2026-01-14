-- Migration script to add 'category' column to measurement_entries table
-- Run this SQL command in your PostgreSQL database

-- Check if column exists and add it if it doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'measurement_entries' 
        AND column_name = 'category'
    ) THEN
        ALTER TABLE measurement_entries ADD COLUMN category VARCHAR;
        RAISE NOTICE 'Column category added to measurement_entries table';
    ELSE
        RAISE NOTICE 'Column category already exists in measurement_entries table';
    END IF;
END $$;
