-- Migration 004: Rename wp_* custom tables to articulate_* prefix
-- Only renames our custom application tables, NOT WordPress core tables
-- Note: Table renames applied via direct SQL; this migration records the change

SELECT 'Tables renamed from wp_* to articulate_* prefix' AS status
