# DOC-01 — Project Charter
**Status:** Draft for review | **Version:** 0.1 | **Date:** 2026-10-10

## Vision
OpsControl is a unified, multi-organization operations console for monitoring ETL workloads, infrastructure, integrations, operational evidence and actionable alerts. It prioritizes readable operational status and rapid investigation.

## Problem
Operators currently switch between Pentaho dashboards, VM consoles, cloud consoles, logs, and incident tools to determine whether scheduled processing succeeded, what failed, and whom to notify.

## Objectives
1. Present a consistent, organization-scoped operational view of jobs, data sources, metrics, logs, and alerts.
2. Make monitoring templates deployable configurations tied to actual data sources and collectors.
3. Preserve evidence and execution history, including step-level Pentaho information when available.
4. Surface alerts and investigations with traceable, non-speculative evidence.
5. Enable maintainable and secure integration with external systems.

## Intended users
- NOC operator: monitors execution, acknowledges/escalates problems, reviews evidence.
- Support engineer: investigates failures and collector health.
- Organization administrator: manages sources, templates, permissions and integrations.
- Platform administrator: maintains shared platform and tenant boundaries.
Roles and precise privileges are proposed; final RBAC matrix requires approval.

## In scope
Organization isolation; resource/data-source management; collectors; metric and log definitions; Pentaho job monitoring; VM, API, SFTP, S3 and database monitoring; alerting; correlation; notification integration; dashboards; audit and configuration history.

## Out of scope for initial monitoring release
Automatic production remediation, arbitrary remote command execution, provisioning EKS clusters, and AI-generated root-cause claims presented as verified facts. These require separate design and security approval.

## Technology direction
Existing React/Vite frontend, FastAPI backend, PostgreSQL and Alembic migrations. Modular monolith initially; deployment automation follows product functionality.

## Success criteria (proposed, not yet measured)
- A newly configured source can be monitored without code changes.
- Operator can distinguish source failure from collector outage.
- Tenant boundaries are enforced in API queries and UI.
- Alerts produce deduplicated, auditable notifications.
- Core workflows pass automated acceptance tests.
- Setup and operator runbooks are reproducible.

## Stakeholder decisions needed
Release-1 monitoring priorities; actual Pentaho read APIs and credentials strategy; roles and access rules; data retention; availability/SLO targets; permitted environments and notification endpoints.
