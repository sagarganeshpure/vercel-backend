
-- SQL to add missing columns to production_papers table
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS total_quantity VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS wall_type VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS rebate VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS sub_frame VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS construction VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS cover_moulding VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS frontside_laminate VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS backside_laminate VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS grade VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS side_frame VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS filler VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS foam_bottom VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS frp_coating VARCHAR;
