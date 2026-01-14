-- Migration script to add missing database columns
-- Run this script in your PostgreSQL database

-- Add site_location column to measurements table
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS site_location VARCHAR;

-- Add po_number column to production_papers table (if it doesn't exist)
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR;

-- Verify columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'measurements' AND column_name = 'site_location';

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'production_papers' AND column_name = 'po_number';
