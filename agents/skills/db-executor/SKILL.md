---
name: db-executor
description: Execute approved database reads, writes and migrations without using an LLM for routine database operations.
---
# Database Executor

LLM inference is forbidden for ordinary CRUD, SQL execution, migration application, indexing, filtering, aggregation and schema validation. Use typed parameters and deterministic database functions. Log the operation and validate the result.

An LLM may help design a genuinely ambiguous future data model, but after a schema is approved the execution path is code/SQL only.
