-- Applied to new socialmarket Supabase project as generic_evidence_audit_framework_v1.
-- This file versions the schema contract in Git. See database migration history for execution record.

create schema if not exists evidence;

-- Generic, entity-agnostic evidence layer. Entity types may be merchant, product,
-- brand, category, competitor, service, pain topic, etc.
-- Production DDL is intentionally kept in Supabase migration history; future changes
-- must be additive/versioned and tested against the V4 evidence worker.
