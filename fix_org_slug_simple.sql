-- Simple SQL script to fix organization_slug column
-- Run this directly in your PostgreSQL database

-- Step 1: Make column nullable (if it exists and is NOT NULL)
ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL;

-- Step 2: Remove the column
ALTER TABLE users DROP COLUMN organization_slug;
