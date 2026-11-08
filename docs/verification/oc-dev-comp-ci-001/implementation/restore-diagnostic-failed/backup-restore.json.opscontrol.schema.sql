--
-- PostgreSQL database dump
--

\restrict VYZp7kxk38cBFvkBRybL6dUosIAbBo2S46aFh7epkWP609tRBHTCOYDbX1ihDrw

-- Dumped from database version 17.11
-- Dumped by pg_dump version 17.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: executionstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.executionstatus AS ENUM (
    'SUCCESS',
    'FAILED',
    'RUNNING',
    'LONG_RUNNING',
    'NO_RUN',
    'NO_RESPONSE',
    'DELAYED',
    'UNKNOWN'
);


--
-- Name: executiontype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.executiontype AS ENUM (
    'SCHEDULED',
    'MANUAL'
);


--
-- Name: investigationstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.investigationstatus AS ENUM (
    'NEW',
    'ACKNOWLEDGED',
    'INVESTIGATING',
    'ROOT_CAUSE_IDENTIFIED',
    'RECOVERY_IN_PROGRESS',
    'MONITORING',
    'RESOLVED'
);


--
-- Name: access_boundary_audit_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.access_boundary_audit_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN RAISE EXCEPTION 'Access boundary decision history is immutable'; END $$;


--
-- Name: k8s_association_decision_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.k8s_association_decision_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN RAISE EXCEPTION 'Kubernetes association history is immutable'; END $$;


--
-- Name: k8s_association_revision_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.k8s_association_revision_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Kubernetes association cannot be deleted';
          END IF;
          IF NEW.id != OLD.id OR NEW.cluster_id != OLD.cluster_id OR
             NEW.organization_id != OLD.organization_id OR NEW.created_at != OLD.created_at OR
             NEW.revision != OLD.revision + 1 OR NEW.active = OLD.active THEN
            RAISE EXCEPTION 'Invalid Kubernetes association revision';
          END IF;
          RETURN NEW;
        END $$;


--
-- Name: k8s_cluster_identity_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.k8s_cluster_identity_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN RAISE EXCEPTION 'Canonical Kubernetes cluster identity is immutable'; END $$;


--
-- Name: native_recovery_evidence_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.native_recovery_evidence_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN RAISE EXCEPTION 'Native incident failure and recovery evidence is immutable and protected'; END $$;


--
-- Name: opscontrol_incident_activity_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.opscontrol_incident_activity_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN RAISE EXCEPTION 'Incident activity is append-only'; END; $$;


--
-- Name: opscontrol_parameter_immutable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.opscontrol_parameter_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
      BEGIN IF TG_OP='DELETE' THEN RAISE EXCEPTION 'parameter versions are immutable'; END IF; IF NEW.configuration IS DISTINCT FROM OLD.configuration OR NEW.resource_id IS DISTINCT FROM OLD.resource_id
      OR NEW.version IS DISTINCT FROM OLD.version OR NEW.sha256 IS DISTINCT FROM OLD.sha256
      OR NEW.organization_id IS DISTINCT FROM OLD.organization_id THEN RAISE EXCEPTION 'parameter versions are immutable'; END IF; RETURN NEW; END $$;


--
-- Name: opscontrol_registry_immutable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.opscontrol_registry_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN RAISE EXCEPTION 'Registry versions are immutable; add a new version'; END; $$;


--
-- Name: opscontrol_reject_audit_mutation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.opscontrol_reject_audit_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION 'Security audit events are append-only';
        END;
        $$;


--
-- Name: opscontrol_resource_identity_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.opscontrol_resource_identity_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE parent_org uuid; source_id uuid;
    BEGIN
      IF NEW.vm_id IS NOT NULL THEN SELECT organization_id INTO parent_org FROM vms WHERE id=NEW.vm_id;
        IF parent_org IS DISTINCT FROM NEW.organization_id THEN RAISE EXCEPTION 'resource VM scope mismatch'; END IF; END IF;
      IF NEW.linked_vm_id IS NOT NULL THEN SELECT organization_id INTO parent_org FROM vms WHERE id=NEW.linked_vm_id;
        IF parent_org IS DISTINCT FROM NEW.organization_id THEN RAISE EXCEPTION 'linked VM scope mismatch'; END IF; END IF;
      IF NEW.job_order_id IS NOT NULL THEN SELECT organization_id INTO parent_org FROM job_orders WHERE id=NEW.job_order_id;
        IF parent_org IS DISTINCT FROM NEW.organization_id THEN RAISE EXCEPTION 'job scope mismatch'; END IF; END IF;
      IF NEW.data_source_id IS NOT NULL THEN SELECT organization_id INTO parent_org FROM data_sources WHERE id=NEW.data_source_id;
        IF parent_org IS DISTINCT FROM NEW.organization_id THEN RAISE EXCEPTION 'source scope mismatch'; END IF; END IF;
      IF NEW.primary_collector_id IS NOT NULL THEN SELECT data_source_id INTO source_id FROM collectors WHERE id=NEW.primary_collector_id;
        IF source_id IS DISTINCT FROM NEW.data_source_id THEN RAISE EXCEPTION 'collector source mismatch'; END IF; END IF;
      RETURN NEW;
    END $$;


--
-- Name: opscontrol_runtime_scope_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.opscontrol_runtime_scope_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN IF NOT EXISTS (SELECT 1 FROM collectors c JOIN data_sources s ON s.id=c.data_source_id WHERE c.id=NEW.collector_id AND s.organization_id=NEW.organization_id) THEN RAISE EXCEPTION 'Collector runtime state tenant mismatch'; END IF; RETURN NEW; END; $$;


--
-- Name: opscontrol_single_department(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.opscontrol_single_department() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
      BEGIN
        IF NEW.active AND (TG_OP='INSERT' OR NOT OLD.active OR NEW.user_id<>OLD.user_id OR NEW.department_id<>OLD.department_id) THEN
          PERFORM id FROM users WHERE id=NEW.user_id FOR UPDATE;
          IF EXISTS(SELECT 1 FROM department_memberships WHERE user_id=NEW.user_id AND active AND id<>NEW.id) THEN
            RAISE EXCEPTION 'Employee already has an active department' USING ERRCODE='23514';
          END IF;
        END IF;
        RETURN NEW;
      END $$;


--
-- Name: pentaho_append_only(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pentaho_append_only() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN RAISE EXCEPTION 'Pentaho immutable identity/evidence/decision is protected'; END $$;


--
-- Name: pentaho_attempt_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pentaho_attempt_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho attempt history is protected'; END IF;
      IF (NEW.organization_id,NEW.resource_id,NEW.history_id,NEW.attempt_key,NEW.attempt_order,NEW.native_identity) IS DISTINCT FROM
         (OLD.organization_id,OLD.resource_id,OLD.history_id,OLD.attempt_key,OLD.attempt_order,OLD.native_identity)
      THEN RAISE EXCEPTION 'Pentaho attempt identity is immutable'; END IF;
      RETURN NEW;
    END $$;


--
-- Name: pentaho_event_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pentaho_event_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      IF OLD.payload ? 'pentaho_identity' THEN
        IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho source evidence is protected'; END IF;
        IF NEW.payload IS DISTINCT FROM OLD.payload THEN RAISE EXCEPTION 'Pentaho source evidence is immutable'; END IF;
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$;


--
-- Name: pentaho_history_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pentaho_history_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        IF OLD.pentaho_resource_id IS NOT NULL THEN RAISE EXCEPTION 'Pentaho history is protected'; END IF;
        RETURN OLD;
      END IF;
      IF OLD.pentaho_resource_id IS NOT NULL AND (NEW.pentaho_customer_id,NEW.pentaho_resource_id,NEW.job_order_id,NEW.provider_execution_id) IS DISTINCT FROM (OLD.pentaho_customer_id,OLD.pentaho_resource_id,OLD.job_order_id,OLD.provider_execution_id)
      THEN RAISE EXCEPTION 'Pentaho logical execution identity is immutable'; END IF;
      RETURN NEW;
    END $$;


--
-- Name: pentaho_inbox_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pentaho_inbox_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      IF OLD.historical_notice_id IS NOT NULL THEN RAISE EXCEPTION 'Historical inbox evidence is protected'; END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
    END $$;


--
-- Name: pentaho_notice_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pentaho_notice_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho historical notification evidence is protected'; END IF;
      IF (NEW.id,NEW.organization_id,NEW.resource_id,NEW.history_id,NEW.event_id,NEW.destination_id,NEW.payload,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.organization_id,OLD.resource_id,OLD.history_id,OLD.event_id,OLD.destination_id,OLD.payload,OLD.created_at)
      THEN RAISE EXCEPTION 'Pentaho historical notification evidence is immutable'; END IF;
      RETURN NEW;
    END $$;


--
-- Name: pentaho_occurrence_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pentaho_occurrence_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      IF OLD.pentaho_authority IS NOT NULL THEN
        IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho occurrence history is protected'; END IF;
        IF (NEW.id,NEW.organization_id,NEW.resource_id,NEW.scheduled_at,NEW.deadline,NEW.parameter_version,NEW.pentaho_authority) IS DISTINCT FROM (OLD.id,OLD.organization_id,OLD.resource_id,OLD.scheduled_at,OLD.deadline,OLD.parameter_version,OLD.pentaho_authority)
        THEN RAISE EXCEPTION 'Pentaho occurrence authority is immutable'; END IF;
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$;


--
-- Name: pentaho_review_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pentaho_review_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho evidence review is protected'; END IF;
      IF (NEW.organization_id,NEW.resource_id,NEW.job_order_id,NEW.history_id,NEW.event_id,NEW.source_evidence_id,NEW.category,NEW.claim,NEW.context,NEW.created_at,NEW.id) IS DISTINCT FROM
         (OLD.organization_id,OLD.resource_id,OLD.job_order_id,OLD.history_id,OLD.event_id,OLD.source_evidence_id,OLD.category,OLD.claim,OLD.context,OLD.created_at,OLD.id)
      THEN RAISE EXCEPTION 'Pentaho evidence review identity/context is immutable'; END IF;
      RETURN NEW;
    END $$;


--
-- Name: protect_access_identity(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.protect_access_identity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR (to_jsonb(NEW)->>'service_provider_id') IS DISTINCT FROM (to_jsonb(OLD)->>'service_provider_id') THEN RAISE EXCEPTION 'Identity and provider ownership are immutable'; END IF; RETURN NEW; END $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: access_boundaries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.access_boundaries (
    id uuid NOT NULL,
    service_provider_id uuid NOT NULL,
    user_id uuid,
    department_id uuid,
    kind character varying(24) NOT NULL,
    specification jsonb NOT NULL,
    active boolean NOT NULL,
    revision integer NOT NULL,
    CONSTRAINT ck_boundary_delegate_employee CHECK ((((kind)::text <> 'DELEGATE'::text) OR (user_id IS NOT NULL))),
    CONSTRAINT ck_boundary_kind CHECK ((((kind)::text = ANY ((ARRAY['LIMIT'::character varying, 'DENY'::character varying, 'DELEGATE'::character varying, 'ALL_CUSTOMERS'::character varying])::text[])) AND (revision > 0))),
    CONSTRAINT ck_boundary_specification CHECK ((jsonb_typeof(specification) = 'object'::text)),
    CONSTRAINT ck_boundary_subject CHECK (((user_id IS NULL) <> (department_id IS NULL)))
);


--
-- Name: access_boundary_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.access_boundary_decisions (
    id uuid NOT NULL,
    boundary_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    request_key character varying(120) NOT NULL,
    request_hash character varying(64) NOT NULL,
    reason character varying(2000) NOT NULL,
    revision integer NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT ck_boundary_decision_revision CHECK ((revision > 0))
);


--
-- Name: access_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.access_sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: agent_deployments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_deployments (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    revision integer NOT NULL,
    previous_revision integer,
    status character varying(30) NOT NULL,
    actor_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: agent_registrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_registrations (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    collector_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    consumed_at timestamp with time zone
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: alert_incident_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_incident_events (
    id uuid NOT NULL,
    history_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    source character varying(100) NOT NULL,
    reference character varying(200),
    severity character varying(50),
    "timestamp" timestamp with time zone NOT NULL
);


--
-- Name: alert_notification_deliveries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_notification_deliveries (
    id uuid NOT NULL,
    alert_state_id uuid NOT NULL,
    channel character varying(50) NOT NULL,
    event_type character varying(30) NOT NULL,
    status character varying(30) DEFAULT 'PENDING'::character varying NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    external_reference character varying(500),
    last_error text,
    sent_at timestamp with time zone,
    payload json,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    lease_token uuid,
    lease_expires_at timestamp with time zone
);


--
-- Name: alert_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_rules (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    metric_definition_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    severity character varying(50) DEFAULT 'WARNING'::character varying NOT NULL,
    operator character varying(20) DEFAULT 'GT'::character varying NOT NULL,
    threshold_value character varying(100) NOT NULL,
    evaluation_window_seconds integer DEFAULT 60 NOT NULL,
    consecutive_breaches integer DEFAULT 1 NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    notification_channels json,
    evaluation_config jsonb
);


--
-- Name: alert_states; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_states (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    alert_rule_id uuid NOT NULL,
    metric_definition_id uuid NOT NULL,
    status character varying(20) DEFAULT 'OPEN'::character varying NOT NULL,
    severity character varying(50) NOT NULL,
    first_triggered_at timestamp with time zone NOT NULL,
    last_evaluated_at timestamp with time zone NOT NULL,
    resolved_at timestamp with time zone,
    last_value double precision NOT NULL,
    breach_count integer DEFAULT 0 NOT NULL,
    message text NOT NULL,
    external_references json,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    acknowledged_at timestamp with time zone,
    acknowledged_by uuid
);


--
-- Name: applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.applications (
    id uuid NOT NULL,
    vm_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    app_type character varying(100),
    monitoring_enabled boolean DEFAULT true NOT NULL
);


--
-- Name: attribute_registry_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attribute_registry_versions (
    id uuid NOT NULL,
    version integer NOT NULL,
    definitions jsonb NOT NULL,
    capabilities jsonb NOT NULL,
    sha256 character varying(64) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_attribute_registry_version CHECK ((version > 0))
);


--
-- Name: auth_throttle_buckets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_throttle_buckets (
    key_hash character varying(64) NOT NULL,
    window_started_at timestamp with time zone NOT NULL,
    attempts integer DEFAULT 0 NOT NULL
);


--
-- Name: collector_config_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collector_config_versions (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    collector_id uuid NOT NULL,
    revision integer NOT NULL,
    yaml_text text NOT NULL,
    sha256 character varying(64) NOT NULL,
    runtime_version character varying(80) NOT NULL,
    validation_status character varying(30) NOT NULL,
    method_snapshot jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    agent_configuration jsonb NOT NULL
);


--
-- Name: collector_methods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collector_methods (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    collector_id uuid NOT NULL,
    name character varying(160) NOT NULL,
    method_type character varying(30) NOT NULL,
    configuration jsonb NOT NULL,
    enabled boolean NOT NULL,
    validation_status character varying(30) NOT NULL,
    revision integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: collector_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collector_runs (
    id uuid NOT NULL,
    collector_id uuid NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    status character varying(50) NOT NULL,
    outcome character varying(100),
    http_status integer,
    response_time_ms integer,
    response_size_bytes integer,
    response_body text,
    error_message text,
    source_metadata jsonb
);


--
-- Name: collector_runtime_states; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collector_runtime_states (
    collector_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    checkpoint jsonb NOT NULL,
    revision integer NOT NULL,
    last_error character varying(80),
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: collectors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collectors (
    id uuid NOT NULL,
    data_source_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    collector_type character varying(100) NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    interval_seconds integer DEFAULT 60 NOT NULL,
    configuration json,
    status character varying(50) DEFAULT 'STOPPED'::character varying NOT NULL,
    last_run_at timestamp with time zone,
    last_success_at timestamp with time zone,
    last_error_at timestamp with time zone,
    last_error text,
    next_run_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    remote_worker_id uuid
);


--
-- Name: correlation_evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.correlation_evidence (
    id uuid NOT NULL,
    correlation_id uuid NOT NULL,
    evidence_type character varying(50) NOT NULL,
    source_id uuid NOT NULL,
    resource_type character varying(100),
    resource_id uuid,
    observed_at timestamp with time zone NOT NULL,
    severity character varying(50),
    relationship character varying(100) NOT NULL,
    details json,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: correlation_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.correlation_records (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    history_id uuid NOT NULL,
    anchor_at timestamp with time zone NOT NULL,
    window_start timestamp with time zone NOT NULL,
    window_end timestamp with time zone NOT NULL,
    status character varying(30) DEFAULT 'ANALYZED'::character varying NOT NULL,
    primary_category character varying(100) DEFAULT 'NO_RELATED_EVIDENCE'::character varying NOT NULL,
    confidence character varying(30) DEFAULT 'NONE'::character varying NOT NULL,
    summary text NOT NULL,
    evidence_count integer DEFAULT 0 NOT NULL,
    analysis_version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: customer_access_grants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_access_grants (
    id uuid NOT NULL,
    service_provider_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    user_id uuid,
    department_id uuid,
    role_id uuid,
    effect character varying(5) NOT NULL,
    legacy_membership_id uuid,
    CONSTRAINT ck_grant_effect_role CHECK (((((effect)::text = 'ALLOW'::text) AND (role_id IS NOT NULL)) OR (((effect)::text = 'DENY'::text) AND (user_id IS NOT NULL) AND (role_id IS NULL)))),
    CONSTRAINT ck_grant_one_subject CHECK (((user_id IS NULL) <> (department_id IS NULL)))
);


--
-- Name: data_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_sources (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    source_type character varying(100) NOT NULL,
    description text,
    endpoint character varying(1000),
    auth_type character varying(100),
    connection_config json,
    enabled boolean DEFAULT true NOT NULL,
    status character varying(50) DEFAULT 'UNKNOWN'::character varying NOT NULL,
    last_test_at timestamp with time zone,
    last_error text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    discovery_external_id character varying(512)
);


--
-- Name: department_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.department_memberships (
    id uuid NOT NULL,
    service_provider_id uuid NOT NULL,
    department_id uuid NOT NULL,
    user_id uuid NOT NULL,
    active boolean NOT NULL
);


--
-- Name: department_role_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.department_role_assignments (
    id uuid NOT NULL,
    service_provider_id uuid NOT NULL,
    department_id uuid NOT NULL,
    role_id uuid NOT NULL
);


--
-- Name: departments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.departments (
    id uuid NOT NULL,
    service_provider_id uuid NOT NULL,
    name character varying(160) NOT NULL,
    code character varying(40),
    description character varying(1000),
    manager_id uuid,
    active boolean NOT NULL
);


--
-- Name: event_correlation_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_correlation_groups (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    environment character varying(20) NOT NULL,
    group_key character varying(200) NOT NULL,
    title character varying(300) NOT NULL,
    status character varying(20) NOT NULL,
    confidence character varying(40) NOT NULL,
    evidence jsonb NOT NULL,
    opened_at timestamp with time zone NOT NULL,
    last_observed_at timestamp with time zone NOT NULL,
    resolved_at timestamp with time zone
);


--
-- Name: event_correlation_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_correlation_members (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    group_id uuid NOT NULL,
    condition_id uuid NOT NULL,
    relationship_id uuid,
    added_at timestamp with time zone NOT NULL,
    evidence jsonb NOT NULL
);


--
-- Name: expected_execution_windows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expected_execution_windows (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    resource_id uuid NOT NULL,
    scheduled_at timestamp with time zone NOT NULL,
    deadline timestamp with time zone NOT NULL,
    status character varying(20) NOT NULL,
    history_id uuid,
    parameter_version integer NOT NULL,
    evaluated_at timestamp with time zone,
    evidence jsonb NOT NULL,
    pentaho_authority jsonb,
    CONSTRAINT ck_schedule_deadline CHECK ((deadline >= scheduled_at))
);


--
-- Name: in_app_notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.in_app_notifications (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    user_id uuid NOT NULL,
    delivery_id uuid,
    created_at timestamp with time zone NOT NULL,
    historical_notice_id uuid,
    CONSTRAINT ck_in_app_notice_origin CHECK (((delivery_id IS NULL) <> (historical_notice_id IS NULL)))
);


--
-- Name: incident_activities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.incident_activities (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    incident_id uuid NOT NULL,
    event_type character varying(40) NOT NULL,
    actor character varying(200) NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    text text,
    previous_status character varying(20),
    new_status character varying(20)
);


--
-- Name: infrastructure_evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.infrastructure_evidence (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    data_source_id uuid NOT NULL,
    collector_id uuid NOT NULL,
    collector_run_id uuid NOT NULL,
    observed_at timestamp with time zone NOT NULL,
    provider character varying(50) NOT NULL,
    payload json NOT NULL
);


--
-- Name: investigation_transitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.investigation_transitions (
    id uuid NOT NULL,
    investigation_id uuid NOT NULL,
    previous_status public.investigationstatus NOT NULL,
    new_status public.investigationstatus NOT NULL,
    operator character varying(200) NOT NULL,
    comment text,
    "timestamp" timestamp with time zone NOT NULL
);


--
-- Name: investigations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.investigations (
    id uuid NOT NULL,
    history_id uuid NOT NULL,
    status public.investigationstatus DEFAULT 'NEW'::public.investigationstatus NOT NULL,
    operator character varying(200),
    started_at timestamp with time zone,
    resolved_at timestamp with time zone,
    failure_category character varying(100),
    suspected_cause text,
    confidence character varying(50),
    root_cause text,
    root_cause_status character varying(50)
);


--
-- Name: job_order_histories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_order_histories (
    id uuid NOT NULL,
    job_order_id uuid NOT NULL,
    execution_type public.executiontype NOT NULL,
    status public.executionstatus NOT NULL,
    started_at timestamp with time zone,
    ended_at timestamp with time zone,
    detected_at timestamp with time zone,
    expected_runtime_seconds integer,
    sla_seconds integer,
    sla_status character varying(50),
    failed_step character varying(200),
    source_error_code character varying(100),
    source_error_message text,
    source_exception text,
    source_log_location character varying(1000),
    source_result character varying(200),
    incident_number character varying(100),
    created_at timestamp with time zone NOT NULL,
    provider_execution_id character varying(200),
    source_evidence json,
    monitoring_conditions jsonb,
    pentaho_customer_id uuid,
    pentaho_resource_id uuid,
    pentaho_lifecycle character varying(25),
    pentaho_outcome character varying(25),
    pentaho_completeness character varying(20),
    pentaho_identity_state character varying(25),
    pentaho_schedule_occurrence jsonb,
    pentaho_review_state character varying(25),
    CONSTRAINT ck_pentaho_history_binding CHECK ((((pentaho_resource_id IS NULL) AND (pentaho_customer_id IS NULL) AND (pentaho_lifecycle IS NULL)) OR ((pentaho_resource_id IS NOT NULL) AND (pentaho_customer_id IS NOT NULL) AND (pentaho_lifecycle IS NOT NULL)))),
    CONSTRAINT ck_pentaho_lifecycle CHECK (((pentaho_lifecycle IS NULL) OR ((pentaho_lifecycle)::text = ANY ((ARRAY['IDENTIFIED'::character varying, 'RUNNING'::character varying, 'WAITING_FOR_RETRY'::character varying, 'TERMINAL'::character varying])::text[])))),
    CONSTRAINT ck_pentaho_outcome CHECK (((pentaho_outcome IS NULL) OR ((pentaho_outcome)::text = ANY ((ARRAY['SUCCESS'::character varying, 'SUCCESS_AFTER_RETRY'::character varying, 'FAILED'::character varying, 'CANCELLED'::character varying, 'UNKNOWN'::character varying])::text[])))),
    CONSTRAINT ck_pentaho_terminal_outcome CHECK (((pentaho_outcome IS NULL) OR ((pentaho_lifecycle)::text = 'TERMINAL'::text)))
);


--
-- Name: job_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_orders (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    vm_id uuid,
    pentaho_instance_id uuid,
    name character varying(200) NOT NULL,
    environment character varying(50) DEFAULT 'PROD'::character varying NOT NULL,
    active boolean DEFAULT true NOT NULL,
    expected_runtime_seconds integer,
    sla_seconds integer,
    schedule json,
    expected_window_start character varying(10),
    expected_window_end character varying(10),
    no_run_grace_seconds integer,
    monitoring_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    host_data_source_id uuid
);


--
-- Name: job_step_executions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_step_executions (
    id uuid NOT NULL,
    history_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    step_type character varying(100),
    status character varying(50) NOT NULL,
    started_at timestamp with time zone,
    ended_at timestamp with time zone,
    duration_seconds integer,
    records_read integer,
    records_written integer,
    records_rejected integer,
    error_code character varying(100),
    error_message text,
    external_step_id character varying(200),
    attempt integer NOT NULL,
    source_evidence jsonb
);


--
-- Name: kubernetes_cluster_association_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kubernetes_cluster_association_decisions (
    id uuid NOT NULL,
    association_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    revision integer NOT NULL,
    active boolean NOT NULL,
    reason character varying(2000) NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_k8s_decision_revision CHECK ((revision > 0))
);


--
-- Name: kubernetes_cluster_associations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kubernetes_cluster_associations (
    id uuid NOT NULL,
    cluster_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    revision integer NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_k8s_association_revision CHECK ((revision > 0))
);


--
-- Name: kubernetes_clusters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kubernetes_clusters (
    id uuid NOT NULL,
    provider_identity character varying(512) NOT NULL,
    provider_cluster_id character varying(128) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: log_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.log_events (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    log_source_id uuid NOT NULL,
    observed_at timestamp with time zone NOT NULL,
    severity character varying(30),
    event_type character varying(100),
    message text NOT NULL,
    parser_type character varying(100),
    source_offset character varying(200),
    fingerprint character varying(128),
    attributes json,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: log_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.log_sources (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    data_source_id uuid,
    collector_id uuid,
    name character varying(200) NOT NULL,
    source_type character varying(100) NOT NULL,
    resource_type character varying(100) NOT NULL,
    resource_id uuid,
    location character varying(1000),
    parser_type character varying(100) DEFAULT 'RAW'::character varying NOT NULL,
    parser_config json,
    start_position character varying(50) DEFAULT 'NEW'::character varying NOT NULL,
    collection_interval_seconds integer DEFAULT 30 NOT NULL,
    retention_days integer DEFAULT 30 NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: managed_agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.managed_agents (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    collector_id uuid NOT NULL,
    worker_id uuid NOT NULL,
    hostname character varying(255) NOT NULL,
    version character varying(80) NOT NULL,
    runtime_version character varying(80) NOT NULL,
    last_seen_at timestamp with time zone,
    desired_revision integer,
    applied_revision integer,
    health character varying(30) NOT NULL,
    last_error character varying(500),
    enabled boolean NOT NULL,
    method_health jsonb DEFAULT '{}'::jsonb NOT NULL,
    downloaded_revision integer,
    verified_revision integer,
    last_working_revision integer,
    configuration_sha256 character varying(64),
    previous_token_hash character varying(64),
    previous_token_expires_at timestamp with time zone,
    applied_at timestamp with time zone,
    verified_at timestamp with time zone,
    credential_renewed_at timestamp with time zone
);


--
-- Name: metric_definitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.metric_definitions (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    data_source_id uuid,
    collector_id uuid,
    name character varying(200) NOT NULL,
    description text,
    resource_type character varying(100) NOT NULL,
    resource_id uuid,
    metric_type character varying(50) NOT NULL,
    unit character varying(50),
    collection_interval_seconds integer DEFAULT 60 NOT NULL,
    retention_days integer DEFAULT 365 NOT NULL,
    aggregation character varying(50) DEFAULT 'avg'::character varying NOT NULL,
    query_config json,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: metric_samples; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.metric_samples (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    metric_definition_id uuid NOT NULL,
    collector_id uuid,
    collector_run_id uuid,
    observed_at timestamp with time zone NOT NULL,
    value_numeric double precision NOT NULL,
    unit character varying(50),
    dimensions json,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: monitoring_activations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitoring_activations (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    data_source_id uuid NOT NULL,
    collector_id uuid,
    status character varying(24) NOT NULL,
    fingerprint character varying(64) NOT NULL,
    version integer NOT NULL,
    applied_at timestamp with time zone NOT NULL,
    details jsonb NOT NULL
);


--
-- Name: monitoring_resources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitoring_resources (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    domain character varying(10) NOT NULL,
    name character varying(200) NOT NULL,
    environment character varying(20) NOT NULL,
    vm_id uuid,
    job_order_id uuid,
    data_source_id uuid,
    primary_collector_id uuid,
    linked_vm_id uuid,
    configuration jsonb NOT NULL,
    revision integer NOT NULL,
    active boolean NOT NULL,
    activation_status character varying(30) NOT NULL,
    schedule_watermark timestamp with time zone,
    last_engine_attempt_at timestamp with time zone,
    last_engine_success_at timestamp with time zone,
    last_engine_error character varying(80),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_resource_binding CHECK (((((domain)::text = 'VM'::text) AND (vm_id IS NOT NULL) AND (job_order_id IS NULL)) OR (((domain)::text = 'ETL'::text) AND (job_order_id IS NOT NULL) AND (vm_id IS NULL)) OR (((domain)::text = 'API'::text) AND (data_source_id IS NOT NULL) AND (vm_id IS NULL) AND (job_order_id IS NULL)))),
    CONSTRAINT ck_resource_domain CHECK (((domain)::text = ANY ((ARRAY['VM'::character varying, 'ETL'::character varying, 'API'::character varying])::text[]))),
    CONSTRAINT ck_resource_environment CHECK (((environment)::text = ANY ((ARRAY['PROD'::character varying, 'QA'::character varying, 'TEST'::character varying, 'DEV'::character varying, 'SANDBOX'::character varying])::text[])))
);


--
-- Name: monitoring_rule_bindings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitoring_rule_bindings (
    id uuid NOT NULL,
    activation_id uuid NOT NULL,
    rule_version_id uuid NOT NULL,
    materialized_id uuid,
    kind character varying(12) NOT NULL
);


--
-- Name: monitoring_rule_catalogs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitoring_rule_catalogs (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    kind character varying(12) NOT NULL,
    name character varying(160) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_monitoring_catalog_kind CHECK (((kind)::text = ANY ((ARRAY['METRIC'::character varying, 'LOG'::character varying, 'ALERT'::character varying])::text[])))
);


--
-- Name: monitoring_rule_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitoring_rule_versions (
    id uuid NOT NULL,
    catalog_id uuid NOT NULL,
    version integer NOT NULL,
    definition jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_monitoring_rule_version_positive CHECK ((version >= 1))
);


--
-- Name: monitoring_template_attachments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitoring_template_attachments (
    id uuid NOT NULL,
    data_source_id uuid NOT NULL,
    template_id uuid NOT NULL,
    template_version integer NOT NULL,
    priority integer DEFAULT 100 NOT NULL,
    overrides json,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: monitoring_template_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitoring_template_versions (
    id uuid NOT NULL,
    template_id uuid NOT NULL,
    version integer NOT NULL,
    status character varying(30) DEFAULT 'COMMITTED'::character varying NOT NULL,
    package_config json NOT NULL,
    committed_at timestamp with time zone NOT NULL,
    committed_by character varying(200)
);


--
-- Name: monitoring_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monitoring_templates (
    id uuid NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    scope character varying(200) DEFAULT 'VM + Application / Services'::character varying NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    status character varying(30) DEFAULT 'COMMITTED'::character varying NOT NULL,
    package_config json NOT NULL,
    committed_at timestamp with time zone,
    committed_by character varying(200),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: native_incident_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.native_incident_alerts (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    incident_id uuid NOT NULL,
    alert_state_id uuid NOT NULL,
    evidence jsonb NOT NULL,
    added_at timestamp with time zone NOT NULL
);


--
-- Name: native_incident_details; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.native_incident_details (
    incident_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    assigned_user_id uuid,
    revision integer NOT NULL,
    escalation_level integer NOT NULL,
    recovery_started_at timestamp with time zone,
    monitoring_started_at timestamp with time zone,
    monitoring_seconds integer NOT NULL,
    last_checked_at timestamp with time zone,
    verified_at timestamp with time zone,
    evidence jsonb NOT NULL,
    CONSTRAINT ck_native_details_limits CHECK (((revision > 0) AND (escalation_level >= 0) AND (monitoring_seconds >= 60)))
);


--
-- Name: native_incident_failures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.native_incident_failures (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    incident_id uuid NOT NULL,
    resource_id uuid NOT NULL,
    history_id uuid NOT NULL,
    event_id uuid NOT NULL,
    root_key character varying(64),
    occurred_at timestamp with time zone NOT NULL,
    discovered_at timestamp with time zone NOT NULL,
    evidence jsonb NOT NULL,
    reassessment jsonb NOT NULL
);


--
-- Name: native_recovery_assessments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.native_recovery_assessments (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    incident_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    request_key character varying(120) NOT NULL,
    request_hash character varying(64) NOT NULL,
    revision integer NOT NULL,
    result character varying(30) NOT NULL,
    assessed_at timestamp with time zone NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT ck_native_assessment_result CHECK (((revision > 0) AND ((result)::text = ANY ((ARRAY['RECOVERY_CANDIDATE'::character varying, 'VALIDATION_PENDING'::character varying, 'VALIDATED_RECOVERY'::character varying, 'VALIDATION_FAILED'::character varying, 'INSUFFICIENT_EVIDENCE'::character varying])::text[]))))
);


--
-- Name: normalized_telemetry_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.normalized_telemetry_events (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    resource_id uuid NOT NULL,
    external_key character varying(200) NOT NULL,
    source_kind character varying(30) NOT NULL,
    log_event_id uuid,
    history_id uuid,
    observed_at timestamp with time zone NOT NULL,
    received_at timestamp with time zone NOT NULL,
    payload jsonb NOT NULL,
    processing_status character varying(20) NOT NULL,
    processing_error character varying(80),
    parameter_version integer
);


--
-- Name: notification_destinations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_destinations (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(160) NOT NULL,
    channel character varying(20) NOT NULL,
    configuration jsonb NOT NULL,
    enabled boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: operational_incidents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.operational_incidents (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    episode_key character varying(120) NOT NULL,
    source_kind character varying(20) NOT NULL,
    source_reference character varying(200) NOT NULL,
    alert_state_id uuid,
    history_id uuid,
    data_source_id uuid,
    title character varying(300) NOT NULL,
    severity character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    condition_status character varying(20) NOT NULL,
    opened_at timestamp with time zone NOT NULL,
    recovered_at timestamp with time zone,
    resolved_at timestamp with time zone,
    CONSTRAINT ck_incident_condition CHECK (((condition_status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'RECOVERED'::character varying])::text[]))),
    CONSTRAINT ck_incident_status CHECK (((status)::text = ANY ((ARRAY['OPEN'::character varying, 'ACKNOWLEDGED'::character varying, 'INVESTIGATING'::character varying, 'RECOVERY_IN_PROGRESS'::character varying, 'MONITORING'::character varying, 'RESOLVED'::character varying, 'CLOSED'::character varying])::text[])))
);


--
-- Name: operator_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.operator_notes (
    id uuid NOT NULL,
    investigation_id uuid NOT NULL,
    operator character varying(200) NOT NULL,
    text text NOT NULL,
    evidence_reference character varying(1000),
    "timestamp" timestamp with time zone NOT NULL
);


--
-- Name: organization_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_memberships (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    role character varying(24) NOT NULL
);


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    id uuid NOT NULL,
    name character varying(200) NOT NULL,
    code character varying(50) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: pentaho_attempt_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_attempt_revisions (
    resource_id uuid NOT NULL,
    history_id uuid NOT NULL,
    attempt_id uuid NOT NULL,
    event_id uuid NOT NULL,
    source_evidence_id uuid,
    revision integer NOT NULL,
    observation_key character varying(64) NOT NULL,
    disposition character varying(30) NOT NULL,
    payload jsonb NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: pentaho_evidence_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_evidence_decisions (
    resource_id uuid NOT NULL,
    review_id uuid NOT NULL,
    revision integer NOT NULL,
    actor_id uuid NOT NULL,
    action character varying(30) NOT NULL,
    reason text NOT NULL,
    request_key character varying(100) NOT NULL,
    request_hash character varying(64) NOT NULL,
    evidence jsonb NOT NULL,
    projection_before jsonb NOT NULL,
    projection_after jsonb NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_pentaho_evidence_decision_action CHECK (((action)::text = ANY ((ARRAY['DEFER'::character varying, 'REJECT_CLAIM'::character varying, 'ACCEPT_VERIFIED_CLAIM'::character varying, 'ADOPT_LEGACY'::character varying])::text[])))
);


--
-- Name: pentaho_evidence_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_evidence_reviews (
    resource_id uuid NOT NULL,
    job_order_id uuid NOT NULL,
    history_id uuid,
    event_id uuid NOT NULL,
    source_evidence_id uuid,
    category character varying(40) NOT NULL,
    claim character varying(40) NOT NULL,
    status character varying(20) NOT NULL,
    revision integer NOT NULL,
    context jsonb NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_pentaho_review_category CHECK (((category)::text = ANY ((ARRAY['AMBIGUOUS_IDENTITY'::character varying, 'NATIVE_ALIAS_CONFLICT'::character varying, 'RETRY_RELATIONSHIP'::character varying, 'EXECUTION_OUTCOME'::character varying, 'LEGACY_ADOPTION'::character varying, 'RECOVERY_IDENTITY'::character varying])::text[]))),
    CONSTRAINT ck_pentaho_review_status CHECK ((((status)::text = ANY ((ARRAY['OPEN'::character varying, 'ACCEPTED'::character varying, 'REJECTED'::character varying])::text[])) AND (revision >= 1)))
);


--
-- Name: pentaho_execution_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_execution_attempts (
    resource_id uuid NOT NULL,
    history_id uuid NOT NULL,
    attempt_key character varying(100) NOT NULL,
    attempt_order integer NOT NULL,
    native_identity jsonb NOT NULL,
    outcome character varying(20) NOT NULL,
    completeness character varying(20) NOT NULL,
    started_at timestamp with time zone,
    ended_at timestamp with time zone,
    retry_authority jsonb NOT NULL,
    revision integer NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_pentaho_attempt_completeness CHECK (((completeness)::text = ANY ((ARRAY['PARTIAL'::character varying, 'COMPLETE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT ck_pentaho_attempt_order CHECK (((attempt_order >= 1) AND (attempt_order <= 10000))),
    CONSTRAINT ck_pentaho_attempt_outcome CHECK (((outcome)::text = ANY ((ARRAY['RUNNING'::character varying, 'SUCCESS'::character varying, 'FAILED'::character varying, 'CANCELLED'::character varying, 'UNKNOWN'::character varying])::text[])))
);


--
-- Name: pentaho_historical_notices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_historical_notices (
    resource_id uuid NOT NULL,
    history_id uuid NOT NULL,
    event_id uuid NOT NULL,
    destination_id uuid NOT NULL,
    payload jsonb NOT NULL,
    status character varying(20) NOT NULL,
    attempts integer NOT NULL,
    lease_token uuid,
    lease_until timestamp with time zone,
    next_attempt_at timestamp with time zone NOT NULL,
    sent_at timestamp with time zone,
    last_error character varying(160),
    external_reference character varying(500),
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_pentaho_notice_status CHECK ((((status)::text = ANY ((ARRAY['PENDING'::character varying, 'PROCESSING'::character varying, 'SENT'::character varying, 'FAILED'::character varying, 'BLOCKED'::character varying])::text[])) AND (attempts >= 0)))
);


--
-- Name: pentaho_instances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_instances (
    id uuid NOT NULL,
    vm_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    base_url character varying(500),
    repository_name character varying(200),
    active boolean DEFAULT true NOT NULL
);


--
-- Name: pentaho_native_aliases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_native_aliases (
    resource_id uuid NOT NULL,
    history_id uuid NOT NULL,
    attempt_id uuid,
    alias_key character varying(100) NOT NULL,
    kind character varying(25) NOT NULL,
    native_identity jsonb NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_pentaho_alias_kind CHECK (((kind)::text = ANY ((ARRAY['INVOCATION'::character varying, 'LOGICAL'::character varying, 'SCHEDULER_ATTEMPT'::character varying])::text[])))
);


--
-- Name: pentaho_recovery_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_recovery_decisions (
    link_id uuid NOT NULL,
    revision integer NOT NULL,
    action character varying(20) NOT NULL,
    actor_id uuid NOT NULL,
    request_key character varying(100) NOT NULL,
    request_hash character varying(64) NOT NULL,
    reason text NOT NULL,
    evidence jsonb NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_pentaho_recovery_action CHECK (((action)::text = ANY ((ARRAY['PROPOSE'::character varying, 'CONFIRM'::character varying, 'REVERSE'::character varying])::text[])))
);


--
-- Name: pentaho_recovery_links; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pentaho_recovery_links (
    failed_history_id uuid NOT NULL,
    recovery_history_id uuid NOT NULL,
    status character varying(20) NOT NULL,
    revision integer NOT NULL,
    proposed_by uuid NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_pentaho_recovery_not_self CHECK ((failed_history_id <> recovery_history_id)),
    CONSTRAINT ck_pentaho_recovery_status CHECK (((status)::text = ANY ((ARRAY['PROPOSED'::character varying, 'CONFIRMED'::character varying, 'REVERSED'::character varying])::text[])))
);


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    key character varying(100) NOT NULL,
    description character varying(240) NOT NULL,
    delegable boolean NOT NULL
);


--
-- Name: pipeline_associations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_associations (
    method_id uuid NOT NULL,
    job_id uuid NOT NULL,
    generation uuid NOT NULL,
    confirmed_by uuid NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL
);


--
-- Name: pipeline_capabilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_capabilities (
    integration_id uuid NOT NULL,
    platform_version character varying(100) NOT NULL,
    edition character varying(100) NOT NULL,
    deployment_type character varying(50) NOT NULL,
    definition jsonb NOT NULL,
    compatibility character varying(20) NOT NULL,
    evidence_status character varying(25) NOT NULL,
    verification_evidence_id uuid,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL,
    CONSTRAINT ck_pipeline_capability_evidence CHECK (((evidence_status)::text = ANY ((ARRAY['DOCUMENTED'::character varying, 'RUNTIME_VERIFIED'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT ck_pipeline_compatibility CHECK (((compatibility)::text = ANY ((ARRAY['SUPPORTED'::character varying, 'CONDITIONAL'::character varying, 'UNSUPPORTED'::character varying, 'UNVERIFIED'::character varying])::text[])))
);


--
-- Name: pipeline_connections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_connections (
    integration_id uuid NOT NULL,
    version integer NOT NULL,
    configuration jsonb NOT NULL,
    checksum character varying(64) NOT NULL,
    active boolean NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL
);


--
-- Name: pipeline_evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_evidence (
    source_id uuid NOT NULL,
    generation uuid NOT NULL,
    external_key character varying(500) NOT NULL,
    native_job_id character varying(500),
    payload jsonb NOT NULL,
    outcome character varying(30) NOT NULL,
    observed_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL
);


--
-- Name: pipeline_holds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_holds (
    source_id uuid NOT NULL,
    kind character varying(20) NOT NULL,
    reference character varying(120) NOT NULL,
    actor_id uuid,
    released_at timestamp with time zone,
    released_by uuid,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL,
    CONSTRAINT ck_pipeline_hold_kind CHECK (((kind)::text = ANY ((ARRAY['INTEGRATION'::character varying, 'MANUAL'::character varying, 'LEGAL'::character varying, 'CONTINUITY'::character varying])::text[])))
);


--
-- Name: pipeline_integrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_integrations (
    name character varying(200) NOT NULL,
    platform character varying(30) NOT NULL,
    environment character varying(20) NOT NULL,
    vm_resource_id uuid,
    configuration jsonb NOT NULL,
    stage integer NOT NULL,
    enabled boolean NOT NULL,
    deleted_at timestamp with time zone,
    owner_id uuid NOT NULL,
    last_discovery_at timestamp with time zone,
    last_redetection_at timestamp with time zone,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL,
    CONSTRAINT ck_pipeline_environment CHECK (((environment)::text = ANY ((ARRAY['PROD'::character varying, 'QA'::character varying, 'TEST'::character varying, 'DEV'::character varying, 'SANDBOX'::character varying])::text[]))),
    CONSTRAINT ck_pipeline_stage CHECK (((stage >= 1) AND (stage <= 8)))
);


--
-- Name: pipeline_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_jobs (
    integration_id uuid NOT NULL,
    native_id character varying(500) NOT NULL,
    name character varying(200) NOT NULL,
    origin character varying(20) NOT NULL,
    selected boolean NOT NULL,
    quarantined boolean NOT NULL,
    stale_since timestamp with time zone,
    last_seen_at timestamp with time zone,
    resource_id uuid,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL
);


--
-- Name: pipeline_methods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_methods (
    integration_id uuid NOT NULL,
    source_id uuid NOT NULL,
    connection_id uuid NOT NULL,
    capability_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    transport character varying(15) NOT NULL,
    configuration jsonb NOT NULL,
    enabled boolean NOT NULL,
    validation character varying(20) NOT NULL,
    last_error character varying(80),
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL,
    CONSTRAINT ck_pipeline_transport CHECK (((transport)::text = ANY ((ARRAY['BACKEND'::character varying, 'AGENT'::character varying])::text[])))
);


--
-- Name: pipeline_operations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_operations (
    integration_id uuid,
    source_id uuid,
    kind character varying(30) NOT NULL,
    idempotency_key character varying(100) NOT NULL,
    request_hash character varying(64) NOT NULL,
    actor_id uuid,
    reviewer_id uuid,
    state character varying(30) NOT NULL,
    configuration jsonb NOT NULL,
    result jsonb NOT NULL,
    fence bigint NOT NULL,
    owner_id uuid,
    attempts integer NOT NULL,
    lease_until timestamp with time zone,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL
);


--
-- Name: pipeline_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_sources (
    method_type character varying(30) NOT NULL,
    canonical_key character varying(64) NOT NULL,
    identity jsonb NOT NULL,
    generation uuid NOT NULL,
    fence bigint NOT NULL,
    owner_id uuid,
    lease_mode character varying(20) NOT NULL,
    next_run_at timestamp with time zone,
    lease_until timestamp with time zone,
    live_checkpoint jsonb NOT NULL,
    recovery_checkpoint jsonb NOT NULL,
    continuity_validated boolean NOT NULL,
    health character varying(30) NOT NULL,
    last_received_at timestamp with time zone,
    last_observed_at timestamp with time zone,
    legacy_collector_id uuid,
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    revision integer NOT NULL,
    CONSTRAINT ck_pipeline_fence CHECK ((fence >= 0))
);


--
-- Name: remote_probe_evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.remote_probe_evidence (
    id uuid NOT NULL,
    event_id uuid NOT NULL,
    job_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    worker_id uuid NOT NULL,
    observed_at timestamp with time zone NOT NULL,
    result jsonb NOT NULL,
    payload_sha256 character varying(64) NOT NULL,
    received_at timestamp with time zone NOT NULL
);


--
-- Name: remote_probe_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.remote_probe_jobs (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    collector_id uuid NOT NULL,
    assigned_worker_id uuid NOT NULL,
    planned_for timestamp with time zone NOT NULL,
    config_snapshot jsonb NOT NULL,
    state character varying(24) DEFAULT 'QUEUED'::character varying NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    lease_nonce_hash character varying(64),
    lease_expires_at timestamp with time zone,
    run_id uuid,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    CONSTRAINT ck_remote_job_attempts CHECK (((attempts >= 0) AND (attempts <= 3)))
);


--
-- Name: resource_conditions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_conditions (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    resource_id uuid NOT NULL,
    condition_key character varying(200) NOT NULL,
    condition_type character varying(60) NOT NULL,
    active boolean NOT NULL,
    severity character varying(20) NOT NULL,
    message character varying(500) NOT NULL,
    first_observed_at timestamp with time zone NOT NULL,
    last_observed_at timestamp with time zone NOT NULL,
    resolved_at timestamp with time zone,
    alert_state_id uuid,
    evidence jsonb NOT NULL
);


--
-- Name: resource_dependencies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_dependencies (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    resource_id uuid NOT NULL,
    depends_on_id uuid NOT NULL,
    relationship_type character varying(30) NOT NULL,
    service_identity character varying(200) NOT NULL,
    valid_from timestamp with time zone NOT NULL,
    valid_to timestamp with time zone,
    CONSTRAINT ck_dependency_not_self CHECK ((resource_id <> depends_on_id)),
    CONSTRAINT ck_dependency_type CHECK (((relationship_type)::text = ANY ((ARRAY['HOSTED_ON'::character varying, 'REQUIRES_SERVICE'::character varying, 'DEPENDS_ON'::character varying])::text[])))
);


--
-- Name: resource_drafts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_drafts (
    id uuid NOT NULL,
    service_provider_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    organization_id uuid,
    domain character varying(8) NOT NULL,
    name character varying(160) NOT NULL,
    stage integer NOT NULL,
    configuration jsonb NOT NULL,
    revision integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_resource_draft_domain CHECK (((domain)::text = ANY ((ARRAY['VM'::character varying, 'ETL'::character varying, 'API'::character varying])::text[]))),
    CONSTRAINT ck_resource_draft_stage CHECK (((stage >= 1) AND (stage <= 10)))
);


--
-- Name: resource_mapping_issues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_mapping_issues (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_id uuid NOT NULL,
    reason character varying(100) NOT NULL,
    candidates jsonb NOT NULL,
    resolved_at timestamp with time zone
);


--
-- Name: resource_parameter_activations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_parameter_activations (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    resource_id uuid NOT NULL,
    parameter_version integer NOT NULL,
    effective_from timestamp with time zone NOT NULL,
    effective_to timestamp with time zone,
    actor_id uuid
);


--
-- Name: resource_parameter_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_parameter_versions (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    resource_id uuid NOT NULL,
    version integer NOT NULL,
    configuration jsonb NOT NULL,
    sha256 character varying(64) NOT NULL,
    status character varying(20) NOT NULL,
    actor_id uuid,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_parameter_status CHECK (((status)::text = ANY ((ARRAY['VALIDATED'::character varying, 'ACTIVE'::character varying, 'SUPERSEDED'::character varying])::text[])))
);


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_permissions (
    role_id uuid NOT NULL,
    permission_key character varying(100) NOT NULL,
    active boolean DEFAULT true NOT NULL
);


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id uuid NOT NULL,
    service_provider_id uuid NOT NULL,
    name character varying(160) NOT NULL,
    code character varying(80) NOT NULL,
    description character varying(1000),
    active boolean NOT NULL,
    system boolean NOT NULL
);


--
-- Name: security_audit_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.security_audit_events (
    id uuid NOT NULL,
    event_type character varying(80) NOT NULL,
    actor_id uuid,
    organization_id uuid,
    target_type character varying(80),
    target_id character varying(120),
    outcome character varying(20) NOT NULL,
    request_id character varying(100),
    occurred_at timestamp with time zone NOT NULL
);


--
-- Name: service_providers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.service_providers (
    id uuid NOT NULL,
    name character varying(160) NOT NULL,
    code character varying(40) NOT NULL,
    active boolean NOT NULL
);


--
-- Name: telemetry_receipts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.telemetry_receipts (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    signal character varying(10) NOT NULL,
    record_count integer NOT NULL,
    payload_hash character varying(64) NOT NULL,
    received_at timestamp with time zone NOT NULL
);


--
-- Name: trace_spans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trace_spans (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    trace_id character varying(32) NOT NULL,
    span_id character varying(16) NOT NULL,
    name character varying(255) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone NOT NULL,
    attributes jsonb NOT NULL
);


--
-- Name: user_role_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_role_assignments (
    id uuid NOT NULL,
    service_provider_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role_id uuid NOT NULL,
    effect character varying(5) NOT NULL,
    CONSTRAINT ck_employee_role_effect CHECK (((effect)::text = ANY ((ARRAY['ALLOW'::character varying, 'DENY'::character varying])::text[])))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    username character varying(120) NOT NULL,
    password_hash character varying(255) NOT NULL,
    active boolean NOT NULL,
    platform_admin boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    service_provider_id uuid DEFAULT '45c4acb0-64fe-532b-ae18-678c1324902d'::uuid NOT NULL,
    employee_id character varying(80),
    full_name character varying(160) DEFAULT ''::character varying NOT NULL,
    work_email character varying(254),
    notification_preferences jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: vms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vms (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    hostname character varying(200) NOT NULL,
    environment character varying(50) DEFAULT 'PROD'::character varying NOT NULL,
    os character varying(100),
    monitoring_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: worker_identities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.worker_identities (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    token_hash character varying(64) NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    allowed_hosts jsonb DEFAULT '[]'::jsonb NOT NULL,
    allowed_cidrs jsonb DEFAULT '[]'::jsonb NOT NULL,
    last_seen_at timestamp with time zone
);


--
-- Name: access_boundaries access_boundaries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_boundaries
    ADD CONSTRAINT access_boundaries_pkey PRIMARY KEY (id);


--
-- Name: access_boundary_decisions access_boundary_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_boundary_decisions
    ADD CONSTRAINT access_boundary_decisions_pkey PRIMARY KEY (id);


--
-- Name: access_sessions access_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_sessions
    ADD CONSTRAINT access_sessions_pkey PRIMARY KEY (id);


--
-- Name: access_sessions access_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_sessions
    ADD CONSTRAINT access_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: agent_deployments agent_deployments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_deployments
    ADD CONSTRAINT agent_deployments_pkey PRIMARY KEY (id);


--
-- Name: agent_registrations agent_registrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_registrations
    ADD CONSTRAINT agent_registrations_pkey PRIMARY KEY (id);


--
-- Name: agent_registrations agent_registrations_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_registrations
    ADD CONSTRAINT agent_registrations_token_hash_key UNIQUE (token_hash);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: alert_incident_events alert_incident_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_incident_events
    ADD CONSTRAINT alert_incident_events_pkey PRIMARY KEY (id);


--
-- Name: alert_notification_deliveries alert_notification_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_notification_deliveries
    ADD CONSTRAINT alert_notification_deliveries_pkey PRIMARY KEY (id);


--
-- Name: alert_rules alert_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_rules
    ADD CONSTRAINT alert_rules_pkey PRIMARY KEY (id);


--
-- Name: alert_states alert_states_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_states
    ADD CONSTRAINT alert_states_pkey PRIMARY KEY (id);


--
-- Name: applications applications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_pkey PRIMARY KEY (id);


--
-- Name: attribute_registry_versions attribute_registry_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attribute_registry_versions
    ADD CONSTRAINT attribute_registry_versions_pkey PRIMARY KEY (id);


--
-- Name: attribute_registry_versions attribute_registry_versions_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attribute_registry_versions
    ADD CONSTRAINT attribute_registry_versions_version_key UNIQUE (version);


--
-- Name: auth_throttle_buckets auth_throttle_buckets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_throttle_buckets
    ADD CONSTRAINT auth_throttle_buckets_pkey PRIMARY KEY (key_hash);


--
-- Name: collector_config_versions collector_config_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_config_versions
    ADD CONSTRAINT collector_config_versions_pkey PRIMARY KEY (id);


--
-- Name: collector_methods collector_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_methods
    ADD CONSTRAINT collector_methods_pkey PRIMARY KEY (id);


--
-- Name: collector_runs collector_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_runs
    ADD CONSTRAINT collector_runs_pkey PRIMARY KEY (id);


--
-- Name: collector_runtime_states collector_runtime_states_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_runtime_states
    ADD CONSTRAINT collector_runtime_states_pkey PRIMARY KEY (collector_id);


--
-- Name: collectors collectors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collectors
    ADD CONSTRAINT collectors_pkey PRIMARY KEY (id);


--
-- Name: correlation_evidence correlation_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correlation_evidence
    ADD CONSTRAINT correlation_evidence_pkey PRIMARY KEY (id);


--
-- Name: correlation_records correlation_records_history_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correlation_records
    ADD CONSTRAINT correlation_records_history_id_key UNIQUE (history_id);


--
-- Name: correlation_records correlation_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correlation_records
    ADD CONSTRAINT correlation_records_pkey PRIMARY KEY (id);


--
-- Name: customer_access_grants customer_access_grants_legacy_membership_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT customer_access_grants_legacy_membership_id_key UNIQUE (legacy_membership_id);


--
-- Name: customer_access_grants customer_access_grants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT customer_access_grants_pkey PRIMARY KEY (id);


--
-- Name: data_sources data_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_pkey PRIMARY KEY (id);


--
-- Name: department_memberships department_memberships_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_memberships
    ADD CONSTRAINT department_memberships_pkey PRIMARY KEY (id);


--
-- Name: department_role_assignments department_role_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_role_assignments
    ADD CONSTRAINT department_role_assignments_pkey PRIMARY KEY (id);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: event_correlation_groups event_correlation_groups_group_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_groups
    ADD CONSTRAINT event_correlation_groups_group_key_key UNIQUE (group_key);


--
-- Name: event_correlation_groups event_correlation_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_groups
    ADD CONSTRAINT event_correlation_groups_pkey PRIMARY KEY (id);


--
-- Name: event_correlation_members event_correlation_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_members
    ADD CONSTRAINT event_correlation_members_pkey PRIMARY KEY (id);


--
-- Name: expected_execution_windows expected_execution_windows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expected_execution_windows
    ADD CONSTRAINT expected_execution_windows_pkey PRIMARY KEY (id);


--
-- Name: in_app_notifications in_app_notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notifications
    ADD CONSTRAINT in_app_notifications_pkey PRIMARY KEY (id);


--
-- Name: incident_activities incident_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.incident_activities
    ADD CONSTRAINT incident_activities_pkey PRIMARY KEY (id);


--
-- Name: infrastructure_evidence infrastructure_evidence_collector_run_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.infrastructure_evidence
    ADD CONSTRAINT infrastructure_evidence_collector_run_id_key UNIQUE (collector_run_id);


--
-- Name: infrastructure_evidence infrastructure_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.infrastructure_evidence
    ADD CONSTRAINT infrastructure_evidence_pkey PRIMARY KEY (id);


--
-- Name: investigation_transitions investigation_transitions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigation_transitions
    ADD CONSTRAINT investigation_transitions_pkey PRIMARY KEY (id);


--
-- Name: investigations investigations_history_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigations
    ADD CONSTRAINT investigations_history_id_key UNIQUE (history_id);


--
-- Name: investigations investigations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigations
    ADD CONSTRAINT investigations_pkey PRIMARY KEY (id);


--
-- Name: job_order_histories job_order_histories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_order_histories
    ADD CONSTRAINT job_order_histories_pkey PRIMARY KEY (id);


--
-- Name: job_orders job_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_orders
    ADD CONSTRAINT job_orders_pkey PRIMARY KEY (id);


--
-- Name: job_step_executions job_step_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_step_executions
    ADD CONSTRAINT job_step_executions_pkey PRIMARY KEY (id);


--
-- Name: kubernetes_cluster_association_decisions kubernetes_cluster_association_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_cluster_association_decisions
    ADD CONSTRAINT kubernetes_cluster_association_decisions_pkey PRIMARY KEY (id);


--
-- Name: kubernetes_cluster_associations kubernetes_cluster_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_cluster_associations
    ADD CONSTRAINT kubernetes_cluster_associations_pkey PRIMARY KEY (id);


--
-- Name: kubernetes_clusters kubernetes_clusters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_clusters
    ADD CONSTRAINT kubernetes_clusters_pkey PRIMARY KEY (id);


--
-- Name: log_events log_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_events
    ADD CONSTRAINT log_events_pkey PRIMARY KEY (id);


--
-- Name: log_sources log_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_sources
    ADD CONSTRAINT log_sources_pkey PRIMARY KEY (id);


--
-- Name: managed_agents managed_agents_collector_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managed_agents
    ADD CONSTRAINT managed_agents_collector_id_key UNIQUE (collector_id);


--
-- Name: managed_agents managed_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managed_agents
    ADD CONSTRAINT managed_agents_pkey PRIMARY KEY (id);


--
-- Name: managed_agents managed_agents_worker_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managed_agents
    ADD CONSTRAINT managed_agents_worker_id_key UNIQUE (worker_id);


--
-- Name: metric_definitions metric_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_definitions
    ADD CONSTRAINT metric_definitions_pkey PRIMARY KEY (id);


--
-- Name: metric_samples metric_samples_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_samples
    ADD CONSTRAINT metric_samples_pkey PRIMARY KEY (id);


--
-- Name: monitoring_activations monitoring_activations_data_source_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_activations
    ADD CONSTRAINT monitoring_activations_data_source_id_key UNIQUE (data_source_id);


--
-- Name: monitoring_activations monitoring_activations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_activations
    ADD CONSTRAINT monitoring_activations_pkey PRIMARY KEY (id);


--
-- Name: monitoring_resources monitoring_resources_data_source_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_data_source_id_key UNIQUE (data_source_id);


--
-- Name: monitoring_resources monitoring_resources_job_order_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_job_order_id_key UNIQUE (job_order_id);


--
-- Name: monitoring_resources monitoring_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_pkey PRIMARY KEY (id);


--
-- Name: monitoring_resources monitoring_resources_vm_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_vm_id_key UNIQUE (vm_id);


--
-- Name: monitoring_rule_bindings monitoring_rule_bindings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_bindings
    ADD CONSTRAINT monitoring_rule_bindings_pkey PRIMARY KEY (id);


--
-- Name: monitoring_rule_catalogs monitoring_rule_catalogs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_catalogs
    ADD CONSTRAINT monitoring_rule_catalogs_pkey PRIMARY KEY (id);


--
-- Name: monitoring_rule_versions monitoring_rule_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_versions
    ADD CONSTRAINT monitoring_rule_versions_pkey PRIMARY KEY (id);


--
-- Name: monitoring_template_attachments monitoring_template_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_template_attachments
    ADD CONSTRAINT monitoring_template_attachments_pkey PRIMARY KEY (id);


--
-- Name: monitoring_template_versions monitoring_template_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_template_versions
    ADD CONSTRAINT monitoring_template_versions_pkey PRIMARY KEY (id);


--
-- Name: monitoring_templates monitoring_templates_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_templates
    ADD CONSTRAINT monitoring_templates_name_key UNIQUE (name);


--
-- Name: monitoring_templates monitoring_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_templates
    ADD CONSTRAINT monitoring_templates_pkey PRIMARY KEY (id);


--
-- Name: native_incident_alerts native_incident_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_alerts
    ADD CONSTRAINT native_incident_alerts_pkey PRIMARY KEY (id);


--
-- Name: native_incident_details native_incident_details_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_details
    ADD CONSTRAINT native_incident_details_pkey PRIMARY KEY (incident_id);


--
-- Name: native_incident_failures native_incident_failures_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_failures
    ADD CONSTRAINT native_incident_failures_event_id_key UNIQUE (event_id);


--
-- Name: native_incident_failures native_incident_failures_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_failures
    ADD CONSTRAINT native_incident_failures_pkey PRIMARY KEY (id);


--
-- Name: native_recovery_assessments native_recovery_assessments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_recovery_assessments
    ADD CONSTRAINT native_recovery_assessments_pkey PRIMARY KEY (id);


--
-- Name: normalized_telemetry_events normalized_telemetry_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_telemetry_events
    ADD CONSTRAINT normalized_telemetry_events_pkey PRIMARY KEY (id);


--
-- Name: notification_destinations notification_destinations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_destinations
    ADD CONSTRAINT notification_destinations_pkey PRIMARY KEY (id);


--
-- Name: operational_incidents operational_incidents_episode_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operational_incidents
    ADD CONSTRAINT operational_incidents_episode_key_key UNIQUE (episode_key);


--
-- Name: operational_incidents operational_incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operational_incidents
    ADD CONSTRAINT operational_incidents_pkey PRIMARY KEY (id);


--
-- Name: operator_notes operator_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operator_notes
    ADD CONSTRAINT operator_notes_pkey PRIMARY KEY (id);


--
-- Name: organization_memberships organization_memberships_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_memberships
    ADD CONSTRAINT organization_memberships_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_code_key UNIQUE (code);


--
-- Name: organizations organizations_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_name_key UNIQUE (name);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: pentaho_attempt_revisions pentaho_attempt_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT pentaho_attempt_revisions_pkey PRIMARY KEY (id);


--
-- Name: pentaho_evidence_decisions pentaho_evidence_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_decisions
    ADD CONSTRAINT pentaho_evidence_decisions_pkey PRIMARY KEY (id);


--
-- Name: pentaho_evidence_reviews pentaho_evidence_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_reviews
    ADD CONSTRAINT pentaho_evidence_reviews_pkey PRIMARY KEY (id);


--
-- Name: pentaho_execution_attempts pentaho_execution_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_execution_attempts
    ADD CONSTRAINT pentaho_execution_attempts_pkey PRIMARY KEY (id);


--
-- Name: pentaho_historical_notices pentaho_historical_notices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_historical_notices
    ADD CONSTRAINT pentaho_historical_notices_pkey PRIMARY KEY (id);


--
-- Name: pentaho_instances pentaho_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_instances
    ADD CONSTRAINT pentaho_instances_pkey PRIMARY KEY (id);


--
-- Name: pentaho_native_aliases pentaho_native_aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_native_aliases
    ADD CONSTRAINT pentaho_native_aliases_pkey PRIMARY KEY (id);


--
-- Name: pentaho_recovery_decisions pentaho_recovery_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_decisions
    ADD CONSTRAINT pentaho_recovery_decisions_pkey PRIMARY KEY (id);


--
-- Name: pentaho_recovery_links pentaho_recovery_links_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_links
    ADD CONSTRAINT pentaho_recovery_links_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (key);


--
-- Name: pipeline_associations pipeline_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_associations
    ADD CONSTRAINT pipeline_associations_pkey PRIMARY KEY (id);


--
-- Name: pipeline_capabilities pipeline_capabilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_capabilities
    ADD CONSTRAINT pipeline_capabilities_pkey PRIMARY KEY (id);


--
-- Name: pipeline_connections pipeline_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_connections
    ADD CONSTRAINT pipeline_connections_pkey PRIMARY KEY (id);


--
-- Name: pipeline_evidence pipeline_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_evidence
    ADD CONSTRAINT pipeline_evidence_pkey PRIMARY KEY (id);


--
-- Name: pipeline_holds pipeline_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_holds
    ADD CONSTRAINT pipeline_holds_pkey PRIMARY KEY (id);


--
-- Name: pipeline_integrations pipeline_integrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_integrations
    ADD CONSTRAINT pipeline_integrations_pkey PRIMARY KEY (id);


--
-- Name: pipeline_jobs pipeline_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_jobs
    ADD CONSTRAINT pipeline_jobs_pkey PRIMARY KEY (id);


--
-- Name: pipeline_methods pipeline_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_methods
    ADD CONSTRAINT pipeline_methods_pkey PRIMARY KEY (id);


--
-- Name: pipeline_operations pipeline_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_operations
    ADD CONSTRAINT pipeline_operations_pkey PRIMARY KEY (id);


--
-- Name: pipeline_sources pipeline_sources_legacy_collector_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_sources
    ADD CONSTRAINT pipeline_sources_legacy_collector_id_key UNIQUE (legacy_collector_id);


--
-- Name: pipeline_sources pipeline_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_sources
    ADD CONSTRAINT pipeline_sources_pkey PRIMARY KEY (id);


--
-- Name: remote_probe_evidence remote_probe_evidence_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_evidence
    ADD CONSTRAINT remote_probe_evidence_event_id_key UNIQUE (event_id);


--
-- Name: remote_probe_evidence remote_probe_evidence_job_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_evidence
    ADD CONSTRAINT remote_probe_evidence_job_id_key UNIQUE (job_id);


--
-- Name: remote_probe_evidence remote_probe_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_evidence
    ADD CONSTRAINT remote_probe_evidence_pkey PRIMARY KEY (id);


--
-- Name: remote_probe_jobs remote_probe_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_jobs
    ADD CONSTRAINT remote_probe_jobs_pkey PRIMARY KEY (id);


--
-- Name: resource_conditions resource_conditions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_conditions
    ADD CONSTRAINT resource_conditions_pkey PRIMARY KEY (id);


--
-- Name: resource_dependencies resource_dependencies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_dependencies
    ADD CONSTRAINT resource_dependencies_pkey PRIMARY KEY (id);


--
-- Name: resource_drafts resource_drafts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_drafts
    ADD CONSTRAINT resource_drafts_pkey PRIMARY KEY (id);


--
-- Name: resource_mapping_issues resource_mapping_issues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_mapping_issues
    ADD CONSTRAINT resource_mapping_issues_pkey PRIMARY KEY (id);


--
-- Name: resource_parameter_activations resource_parameter_activations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_activations
    ADD CONSTRAINT resource_parameter_activations_pkey PRIMARY KEY (id);


--
-- Name: resource_parameter_versions resource_parameter_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_versions
    ADD CONSTRAINT resource_parameter_versions_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role_id, permission_key);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: security_audit_events security_audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.security_audit_events
    ADD CONSTRAINT security_audit_events_pkey PRIMARY KEY (id);


--
-- Name: service_providers service_providers_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_providers
    ADD CONSTRAINT service_providers_code_key UNIQUE (code);


--
-- Name: service_providers service_providers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_providers
    ADD CONSTRAINT service_providers_pkey PRIMARY KEY (id);


--
-- Name: telemetry_receipts telemetry_receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_receipts
    ADD CONSTRAINT telemetry_receipts_pkey PRIMARY KEY (id);


--
-- Name: trace_spans trace_spans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_spans
    ADD CONSTRAINT trace_spans_pkey PRIMARY KEY (id);


--
-- Name: alert_rules uq_alert_rule_org_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_rules
    ADD CONSTRAINT uq_alert_rule_org_name UNIQUE (organization_id, name);


--
-- Name: alert_states uq_alert_state_org_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_states
    ADD CONSTRAINT uq_alert_state_org_id UNIQUE (organization_id, id);


--
-- Name: applications uq_application_vm_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT uq_application_vm_name UNIQUE (vm_id, name);


--
-- Name: access_boundary_decisions uq_boundary_decision_request; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_boundary_decisions
    ADD CONSTRAINT uq_boundary_decision_request UNIQUE (actor_id, request_key);


--
-- Name: collector_config_versions uq_collector_config_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_config_versions
    ADD CONSTRAINT uq_collector_config_revision UNIQUE (collector_id, revision);


--
-- Name: collectors uq_collector_source_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collectors
    ADD CONSTRAINT uq_collector_source_name UNIQUE (data_source_id, name);


--
-- Name: resource_conditions uq_condition_org_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_conditions
    ADD CONSTRAINT uq_condition_org_id UNIQUE (organization_id, id);


--
-- Name: event_correlation_groups uq_correlation_group_org_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_groups
    ADD CONSTRAINT uq_correlation_group_org_id UNIQUE (organization_id, id);


--
-- Name: event_correlation_members uq_correlation_member; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_members
    ADD CONSTRAINT uq_correlation_member UNIQUE (group_id, condition_id);


--
-- Name: data_sources uq_data_source_org_discovery; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT uq_data_source_org_discovery UNIQUE (organization_id, discovery_external_id);


--
-- Name: data_sources uq_data_source_org_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT uq_data_source_org_name UNIQUE (organization_id, name);


--
-- Name: departments uq_department_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT uq_department_code UNIQUE (service_provider_id, code);


--
-- Name: department_memberships uq_department_employee; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_memberships
    ADD CONSTRAINT uq_department_employee UNIQUE (department_id, user_id);


--
-- Name: departments uq_department_provider; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT uq_department_provider UNIQUE (id, service_provider_id);


--
-- Name: department_role_assignments uq_department_role; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_role_assignments
    ADD CONSTRAINT uq_department_role UNIQUE (department_id, role_id);


--
-- Name: users uq_employee_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_employee_id UNIQUE (service_provider_id, employee_id);


--
-- Name: user_role_assignments uq_employee_role; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role_assignments
    ADD CONSTRAINT uq_employee_role UNIQUE (user_id, role_id);


--
-- Name: expected_execution_windows uq_expected_execution_window; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expected_execution_windows
    ADD CONSTRAINT uq_expected_execution_window UNIQUE (resource_id, scheduled_at);


--
-- Name: in_app_notifications uq_in_app_delivery_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notifications
    ADD CONSTRAINT uq_in_app_delivery_user UNIQUE (delivery_id, user_id);


--
-- Name: in_app_notifications uq_in_app_historical_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notifications
    ADD CONSTRAINT uq_in_app_historical_user UNIQUE (historical_notice_id, user_id);


--
-- Name: job_orders uq_job_order_identity; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_orders
    ADD CONSTRAINT uq_job_order_identity UNIQUE (organization_id, vm_id, name);


--
-- Name: kubernetes_cluster_association_decisions uq_k8s_association_decision_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_cluster_association_decisions
    ADD CONSTRAINT uq_k8s_association_decision_revision UNIQUE (association_id, revision);


--
-- Name: kubernetes_cluster_associations uq_k8s_cluster_customer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_cluster_associations
    ADD CONSTRAINT uq_k8s_cluster_customer UNIQUE (cluster_id, organization_id);


--
-- Name: kubernetes_clusters uq_k8s_verified_cluster_identity; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_clusters
    ADD CONSTRAINT uq_k8s_verified_cluster_identity UNIQUE (provider_identity, provider_cluster_id);


--
-- Name: resource_mapping_issues uq_mapping_issue_entity; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_mapping_issues
    ADD CONSTRAINT uq_mapping_issue_entity UNIQUE (entity_type, entity_id);


--
-- Name: monitoring_rule_bindings uq_monitoring_activation_rule; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_bindings
    ADD CONSTRAINT uq_monitoring_activation_rule UNIQUE (activation_id, rule_version_id);


--
-- Name: monitoring_rule_catalogs uq_monitoring_catalog_org_kind_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_catalogs
    ADD CONSTRAINT uq_monitoring_catalog_org_kind_name UNIQUE (organization_id, kind, name);


--
-- Name: monitoring_resources uq_monitoring_resource_org_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT uq_monitoring_resource_org_id UNIQUE (organization_id, id);


--
-- Name: monitoring_rule_versions uq_monitoring_rule_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_versions
    ADD CONSTRAINT uq_monitoring_rule_version UNIQUE (catalog_id, version);


--
-- Name: monitoring_template_versions uq_monitoring_template_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_template_versions
    ADD CONSTRAINT uq_monitoring_template_version UNIQUE (template_id, version);


--
-- Name: native_recovery_assessments uq_native_assessment_request; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_recovery_assessments
    ADD CONSTRAINT uq_native_assessment_request UNIQUE (organization_id, request_key);


--
-- Name: native_incident_alerts uq_native_incident_alert; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_alerts
    ADD CONSTRAINT uq_native_incident_alert UNIQUE (incident_id, alert_state_id);


--
-- Name: normalized_telemetry_events uq_normalized_event_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_telemetry_events
    ADD CONSTRAINT uq_normalized_event_key UNIQUE (resource_id, external_key);


--
-- Name: normalized_telemetry_events uq_normalized_event_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_telemetry_events
    ADD CONSTRAINT uq_normalized_event_scope UNIQUE (organization_id, resource_id, id);


--
-- Name: notification_destinations uq_notification_destination_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_destinations
    ADD CONSTRAINT uq_notification_destination_name UNIQUE (organization_id, name);


--
-- Name: notification_destinations uq_notification_destination_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_destinations
    ADD CONSTRAINT uq_notification_destination_scope UNIQUE (organization_id, id);


--
-- Name: operational_incidents uq_operational_incident_org_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operational_incidents
    ADD CONSTRAINT uq_operational_incident_org_id UNIQUE (organization_id, id);


--
-- Name: organization_memberships uq_org_membership_user_org; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_memberships
    ADD CONSTRAINT uq_org_membership_user_org UNIQUE (user_id, organization_id);


--
-- Name: pentaho_execution_attempts uq_pentaho_attempt_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_execution_attempts
    ADD CONSTRAINT uq_pentaho_attempt_key UNIQUE (organization_id, resource_id, attempt_key);


--
-- Name: pentaho_execution_attempts uq_pentaho_attempt_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_execution_attempts
    ADD CONSTRAINT uq_pentaho_attempt_order UNIQUE (history_id, attempt_order);


--
-- Name: pentaho_attempt_revisions uq_pentaho_attempt_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT uq_pentaho_attempt_revision UNIQUE (attempt_id, revision);


--
-- Name: pentaho_execution_attempts uq_pentaho_attempt_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_execution_attempts
    ADD CONSTRAINT uq_pentaho_attempt_scope UNIQUE (organization_id, resource_id, history_id, id);


--
-- Name: pentaho_evidence_decisions uq_pentaho_evidence_decision_request; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_decisions
    ADD CONSTRAINT uq_pentaho_evidence_decision_request UNIQUE (organization_id, request_key);


--
-- Name: pentaho_evidence_decisions uq_pentaho_evidence_decision_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_decisions
    ADD CONSTRAINT uq_pentaho_evidence_decision_revision UNIQUE (review_id, revision);


--
-- Name: pentaho_historical_notices uq_pentaho_historical_obligation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_historical_notices
    ADD CONSTRAINT uq_pentaho_historical_obligation UNIQUE (history_id, destination_id);


--
-- Name: job_order_histories uq_pentaho_history_customer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_order_histories
    ADD CONSTRAINT uq_pentaho_history_customer UNIQUE (pentaho_customer_id, id);


--
-- Name: job_order_histories uq_pentaho_history_job; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_order_histories
    ADD CONSTRAINT uq_pentaho_history_job UNIQUE (job_order_id, id);


--
-- Name: job_order_histories uq_pentaho_history_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_order_histories
    ADD CONSTRAINT uq_pentaho_history_scope UNIQUE (pentaho_customer_id, pentaho_resource_id, id);


--
-- Name: pentaho_native_aliases uq_pentaho_native_alias; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_native_aliases
    ADD CONSTRAINT uq_pentaho_native_alias UNIQUE (organization_id, resource_id, alias_key);


--
-- Name: pentaho_historical_notices uq_pentaho_notice_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_historical_notices
    ADD CONSTRAINT uq_pentaho_notice_scope UNIQUE (organization_id, id);


--
-- Name: pentaho_attempt_revisions uq_pentaho_observation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT uq_pentaho_observation UNIQUE (attempt_id, observation_key);


--
-- Name: pentaho_recovery_decisions uq_pentaho_recovery_decision_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_decisions
    ADD CONSTRAINT uq_pentaho_recovery_decision_revision UNIQUE (link_id, revision);


--
-- Name: pentaho_recovery_links uq_pentaho_recovery_pair; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_links
    ADD CONSTRAINT uq_pentaho_recovery_pair UNIQUE (failed_history_id, recovery_history_id);


--
-- Name: pentaho_recovery_decisions uq_pentaho_recovery_request; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_decisions
    ADD CONSTRAINT uq_pentaho_recovery_request UNIQUE (organization_id, request_key);


--
-- Name: pentaho_recovery_links uq_pentaho_recovery_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_links
    ADD CONSTRAINT uq_pentaho_recovery_scope UNIQUE (organization_id, id);


--
-- Name: pentaho_evidence_reviews uq_pentaho_review_event_category; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_reviews
    ADD CONSTRAINT uq_pentaho_review_event_category UNIQUE (event_id, category);


--
-- Name: pentaho_evidence_reviews uq_pentaho_review_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_reviews
    ADD CONSTRAINT uq_pentaho_review_scope UNIQUE (organization_id, resource_id, id);


--
-- Name: pentaho_attempt_revisions uq_pentaho_revision_event; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT uq_pentaho_revision_event UNIQUE (event_id);


--
-- Name: pipeline_associations uq_pipeline_association; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_associations
    ADD CONSTRAINT uq_pipeline_association UNIQUE (method_id, job_id, generation);


--
-- Name: pipeline_associations uq_pipeline_association_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_associations
    ADD CONSTRAINT uq_pipeline_association_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_sources uq_pipeline_canonical_source; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_sources
    ADD CONSTRAINT uq_pipeline_canonical_source UNIQUE (organization_id, canonical_key);


--
-- Name: pipeline_capabilities uq_pipeline_capability_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_capabilities
    ADD CONSTRAINT uq_pipeline_capability_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_connections uq_pipeline_connection_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_connections
    ADD CONSTRAINT uq_pipeline_connection_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_connections uq_pipeline_connection_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_connections
    ADD CONSTRAINT uq_pipeline_connection_version UNIQUE (integration_id, version);


--
-- Name: pipeline_evidence uq_pipeline_evidence_identity; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_evidence
    ADD CONSTRAINT uq_pipeline_evidence_identity UNIQUE (source_id, generation, external_key);


--
-- Name: pipeline_evidence uq_pipeline_evidence_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_evidence
    ADD CONSTRAINT uq_pipeline_evidence_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_holds uq_pipeline_hold_reference; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_holds
    ADD CONSTRAINT uq_pipeline_hold_reference UNIQUE (source_id, kind, reference);


--
-- Name: pipeline_holds uq_pipeline_hold_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_holds
    ADD CONSTRAINT uq_pipeline_hold_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_integrations uq_pipeline_integration_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_integrations
    ADD CONSTRAINT uq_pipeline_integration_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_jobs uq_pipeline_job_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_jobs
    ADD CONSTRAINT uq_pipeline_job_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_methods uq_pipeline_method_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_methods
    ADD CONSTRAINT uq_pipeline_method_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_methods uq_pipeline_method_source; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_methods
    ADD CONSTRAINT uq_pipeline_method_source UNIQUE (integration_id, source_id);


--
-- Name: pipeline_jobs uq_pipeline_native_job; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_jobs
    ADD CONSTRAINT uq_pipeline_native_job UNIQUE (integration_id, native_id);


--
-- Name: pipeline_operations uq_pipeline_operation_idempotency; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_operations
    ADD CONSTRAINT uq_pipeline_operation_idempotency UNIQUE (organization_id, kind, idempotency_key);


--
-- Name: pipeline_operations uq_pipeline_operation_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_operations
    ADD CONSTRAINT uq_pipeline_operation_scope UNIQUE (organization_id, id);


--
-- Name: pipeline_sources uq_pipeline_source_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_sources
    ADD CONSTRAINT uq_pipeline_source_scope UNIQUE (organization_id, id);


--
-- Name: remote_probe_jobs uq_remote_collector_planned; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_jobs
    ADD CONSTRAINT uq_remote_collector_planned UNIQUE (collector_id, planned_for);


--
-- Name: resource_conditions uq_resource_condition; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_conditions
    ADD CONSTRAINT uq_resource_condition UNIQUE (resource_id, condition_key);


--
-- Name: monitoring_resources uq_resource_job_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT uq_resource_job_scope UNIQUE (organization_id, id, job_order_id);


--
-- Name: resource_parameter_versions uq_resource_parameter_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_versions
    ADD CONSTRAINT uq_resource_parameter_version UNIQUE (resource_id, version);


--
-- Name: roles uq_role_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT uq_role_code UNIQUE (service_provider_id, code);


--
-- Name: roles uq_role_provider; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT uq_role_provider UNIQUE (id, service_provider_id);


--
-- Name: telemetry_receipts uq_telemetry_batch; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_receipts
    ADD CONSTRAINT uq_telemetry_batch UNIQUE (agent_id, signal, payload_hash);


--
-- Name: monitoring_template_attachments uq_template_attachment_source_template; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_template_attachments
    ADD CONSTRAINT uq_template_attachment_source_template UNIQUE (data_source_id, template_id);


--
-- Name: users uq_user_provider; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_user_provider UNIQUE (id, service_provider_id);


--
-- Name: vms uq_vm_org_hostname; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vms
    ADD CONSTRAINT uq_vm_org_hostname UNIQUE (organization_id, hostname);


--
-- Name: worker_identities uq_worker_org_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_identities
    ADD CONSTRAINT uq_worker_org_name UNIQUE (organization_id, name);


--
-- Name: user_role_assignments user_role_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role_assignments
    ADD CONSTRAINT user_role_assignments_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: vms vms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vms
    ADD CONSTRAINT vms_pkey PRIMARY KEY (id);


--
-- Name: worker_identities worker_identities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_identities
    ADD CONSTRAINT worker_identities_pkey PRIMARY KEY (id);


--
-- Name: worker_identities worker_identities_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_identities
    ADD CONSTRAINT worker_identities_token_hash_key UNIQUE (token_hash);


--
-- Name: ix_access_boundaries_department_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_access_boundaries_department_id ON public.access_boundaries USING btree (department_id);


--
-- Name: ix_access_boundaries_service_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_access_boundaries_service_provider_id ON public.access_boundaries USING btree (service_provider_id);


--
-- Name: ix_access_boundaries_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_access_boundaries_user_id ON public.access_boundaries USING btree (user_id);


--
-- Name: ix_access_sessions_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_access_sessions_token_hash ON public.access_sessions USING btree (token_hash);


--
-- Name: ix_access_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_access_sessions_user_id ON public.access_sessions USING btree (user_id);


--
-- Name: ix_agent_deployments_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_deployments_agent_id ON public.agent_deployments USING btree (agent_id);


--
-- Name: ix_agent_deployments_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_deployments_organization_id ON public.agent_deployments USING btree (organization_id);


--
-- Name: ix_agent_registrations_collector_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_registrations_collector_id ON public.agent_registrations USING btree (collector_id);


--
-- Name: ix_agent_registrations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_registrations_organization_id ON public.agent_registrations USING btree (organization_id);


--
-- Name: ix_alert_incident_events_history_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_incident_events_history_id ON public.alert_incident_events USING btree (history_id);


--
-- Name: ix_alert_notification_deliveries_alert_state_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_notification_deliveries_alert_state_id ON public.alert_notification_deliveries USING btree (alert_state_id);


--
-- Name: ix_alert_notification_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_notification_pending ON public.alert_notification_deliveries USING btree (status, created_at);


--
-- Name: ix_alert_rules_metric_definition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_rules_metric_definition_id ON public.alert_rules USING btree (metric_definition_id);


--
-- Name: ix_alert_rules_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_rules_organization_id ON public.alert_rules USING btree (organization_id);


--
-- Name: ix_alert_states_alert_rule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_states_alert_rule_id ON public.alert_states USING btree (alert_rule_id);


--
-- Name: ix_alert_states_metric_definition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_states_metric_definition_id ON public.alert_states USING btree (metric_definition_id);


--
-- Name: ix_alert_states_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alert_states_organization_id ON public.alert_states USING btree (organization_id);


--
-- Name: ix_applications_vm_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_vm_id ON public.applications USING btree (vm_id);


--
-- Name: ix_collector_config_versions_collector_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collector_config_versions_collector_id ON public.collector_config_versions USING btree (collector_id);


--
-- Name: ix_collector_config_versions_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collector_config_versions_organization_id ON public.collector_config_versions USING btree (organization_id);


--
-- Name: ix_collector_methods_collector_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collector_methods_collector_id ON public.collector_methods USING btree (collector_id);


--
-- Name: ix_collector_methods_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collector_methods_organization_id ON public.collector_methods USING btree (organization_id);


--
-- Name: ix_collector_runs_collector_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collector_runs_collector_id ON public.collector_runs USING btree (collector_id);


--
-- Name: ix_collector_runs_latest; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collector_runs_latest ON public.collector_runs USING btree (collector_id, started_at DESC, id DESC);


--
-- Name: ix_collector_runtime_states_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collector_runtime_states_organization_id ON public.collector_runtime_states USING btree (organization_id);


--
-- Name: ix_collectors_data_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collectors_data_source_id ON public.collectors USING btree (data_source_id);


--
-- Name: ix_collectors_due_local; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collectors_due_local ON public.collectors USING btree (next_run_at, id) WHERE (enabled AND (remote_worker_id IS NULL));


--
-- Name: ix_collectors_remote_worker_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_collectors_remote_worker_id ON public.collectors USING btree (remote_worker_id);


--
-- Name: ix_correlation_evidence_corr_observed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correlation_evidence_corr_observed ON public.correlation_evidence USING btree (correlation_id, observed_at);


--
-- Name: ix_correlation_evidence_correlation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correlation_evidence_correlation_id ON public.correlation_evidence USING btree (correlation_id);


--
-- Name: ix_correlation_evidence_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correlation_evidence_resource_id ON public.correlation_evidence USING btree (resource_id);


--
-- Name: ix_correlation_evidence_resource_observed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correlation_evidence_resource_observed ON public.correlation_evidence USING btree (resource_id, observed_at);


--
-- Name: ix_correlation_evidence_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correlation_evidence_source_id ON public.correlation_evidence USING btree (source_id);


--
-- Name: ix_correlation_group_inventory; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correlation_group_inventory ON public.event_correlation_groups USING btree (organization_id, environment, opened_at, id);


--
-- Name: ix_correlation_records_history_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correlation_records_history_id ON public.correlation_records USING btree (history_id);


--
-- Name: ix_correlation_records_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correlation_records_organization_id ON public.correlation_records USING btree (organization_id);


--
-- Name: ix_customer_access_grants_department_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_access_grants_department_id ON public.customer_access_grants USING btree (department_id);


--
-- Name: ix_customer_access_grants_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_access_grants_organization_id ON public.customer_access_grants USING btree (organization_id);


--
-- Name: ix_customer_access_grants_role_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_access_grants_role_id ON public.customer_access_grants USING btree (role_id);


--
-- Name: ix_customer_access_grants_service_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_access_grants_service_provider_id ON public.customer_access_grants USING btree (service_provider_id);


--
-- Name: ix_customer_access_grants_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_access_grants_user_id ON public.customer_access_grants USING btree (user_id);


--
-- Name: ix_data_sources_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_data_sources_organization_id ON public.data_sources USING btree (organization_id);


--
-- Name: ix_department_memberships_department_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_department_memberships_department_id ON public.department_memberships USING btree (department_id);


--
-- Name: ix_department_memberships_service_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_department_memberships_service_provider_id ON public.department_memberships USING btree (service_provider_id);


--
-- Name: ix_department_memberships_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_department_memberships_user_id ON public.department_memberships USING btree (user_id);


--
-- Name: ix_department_role_assignments_department_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_department_role_assignments_department_id ON public.department_role_assignments USING btree (department_id);


--
-- Name: ix_department_role_assignments_role_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_department_role_assignments_role_id ON public.department_role_assignments USING btree (role_id);


--
-- Name: ix_department_role_assignments_service_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_department_role_assignments_service_provider_id ON public.department_role_assignments USING btree (service_provider_id);


--
-- Name: ix_departments_service_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_departments_service_provider_id ON public.departments USING btree (service_provider_id);


--
-- Name: ix_draft_owner_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_draft_owner_updated ON public.resource_drafts USING btree (service_provider_id, owner_id, updated_at);


--
-- Name: ix_event_correlation_groups_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_event_correlation_groups_organization_id ON public.event_correlation_groups USING btree (organization_id);


--
-- Name: ix_event_correlation_members_condition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_event_correlation_members_condition_id ON public.event_correlation_members USING btree (condition_id);


--
-- Name: ix_event_correlation_members_group_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_event_correlation_members_group_id ON public.event_correlation_members USING btree (group_id);


--
-- Name: ix_event_correlation_members_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_event_correlation_members_organization_id ON public.event_correlation_members USING btree (organization_id);


--
-- Name: ix_expected_evaluate; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expected_evaluate ON public.expected_execution_windows USING btree (resource_id, status, scheduled_at);


--
-- Name: ix_expected_execution_windows_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expected_execution_windows_organization_id ON public.expected_execution_windows USING btree (organization_id);


--
-- Name: ix_expected_execution_windows_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expected_execution_windows_resource_id ON public.expected_execution_windows USING btree (resource_id);


--
-- Name: ix_in_app_notifications_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_in_app_notifications_organization_id ON public.in_app_notifications USING btree (organization_id);


--
-- Name: ix_in_app_notifications_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_in_app_notifications_user_id ON public.in_app_notifications USING btree (user_id);


--
-- Name: ix_incident_activities_incident_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_incident_activities_incident_id ON public.incident_activities USING btree (incident_id);


--
-- Name: ix_incident_activities_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_incident_activities_organization_id ON public.incident_activities USING btree (organization_id);


--
-- Name: ix_incident_org_opened; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_incident_org_opened ON public.operational_incidents USING btree (organization_id, opened_at);


--
-- Name: ix_infra_evidence_latest; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_infra_evidence_latest ON public.infrastructure_evidence USING btree (collector_id, observed_at DESC, id DESC);


--
-- Name: ix_infrastructure_evidence_collector_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_infrastructure_evidence_collector_id ON public.infrastructure_evidence USING btree (collector_id);


--
-- Name: ix_infrastructure_evidence_data_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_infrastructure_evidence_data_source_id ON public.infrastructure_evidence USING btree (data_source_id);


--
-- Name: ix_infrastructure_evidence_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_infrastructure_evidence_organization_id ON public.infrastructure_evidence USING btree (organization_id);


--
-- Name: ix_investigation_transitions_investigation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_investigation_transitions_investigation_id ON public.investigation_transitions USING btree (investigation_id);


--
-- Name: ix_job_order_histories_job_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_order_histories_job_order_id ON public.job_order_histories USING btree (job_order_id);


--
-- Name: ix_job_orders_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_orders_organization_id ON public.job_orders USING btree (organization_id);


--
-- Name: ix_job_orders_vm_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_orders_vm_id ON public.job_orders USING btree (vm_id);


--
-- Name: ix_job_step_executions_history_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_step_executions_history_id ON public.job_step_executions USING btree (history_id);


--
-- Name: ix_kubernetes_cluster_associations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kubernetes_cluster_associations_organization_id ON public.kubernetes_cluster_associations USING btree (organization_id);


--
-- Name: ix_log_events_fingerprint; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_events_fingerprint ON public.log_events USING btree (fingerprint);


--
-- Name: ix_log_events_log_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_events_log_source_id ON public.log_events USING btree (log_source_id);


--
-- Name: ix_log_events_observed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_events_observed_at ON public.log_events USING btree (observed_at);


--
-- Name: ix_log_events_org_observed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_events_org_observed ON public.log_events USING btree (organization_id, observed_at);


--
-- Name: ix_log_events_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_events_organization_id ON public.log_events USING btree (organization_id);


--
-- Name: ix_log_events_source_observed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_events_source_observed ON public.log_events USING btree (log_source_id, observed_at);


--
-- Name: ix_log_sources_collector_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_sources_collector_id ON public.log_sources USING btree (collector_id);


--
-- Name: ix_log_sources_data_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_sources_data_source_id ON public.log_sources USING btree (data_source_id);


--
-- Name: ix_log_sources_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_sources_organization_id ON public.log_sources USING btree (organization_id);


--
-- Name: ix_log_sources_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_log_sources_resource_id ON public.log_sources USING btree (resource_id);


--
-- Name: ix_managed_agents_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_managed_agents_organization_id ON public.managed_agents USING btree (organization_id);


--
-- Name: ix_metric_definitions_collector_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_definitions_collector_id ON public.metric_definitions USING btree (collector_id);


--
-- Name: ix_metric_definitions_data_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_definitions_data_source_id ON public.metric_definitions USING btree (data_source_id);


--
-- Name: ix_metric_definitions_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_definitions_organization_id ON public.metric_definitions USING btree (organization_id);


--
-- Name: ix_metric_definitions_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_definitions_resource_id ON public.metric_definitions USING btree (resource_id);


--
-- Name: ix_metric_samples_collector_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_collector_id ON public.metric_samples USING btree (collector_id);


--
-- Name: ix_metric_samples_collector_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_collector_run_id ON public.metric_samples USING btree (collector_run_id);


--
-- Name: ix_metric_samples_metric_definition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_metric_definition_id ON public.metric_samples USING btree (metric_definition_id);


--
-- Name: ix_metric_samples_metric_observed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_metric_observed ON public.metric_samples USING btree (metric_definition_id, observed_at);


--
-- Name: ix_metric_samples_org_observed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_org_observed ON public.metric_samples USING btree (organization_id, observed_at);


--
-- Name: ix_monitoring_activations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitoring_activations_organization_id ON public.monitoring_activations USING btree (organization_id);


--
-- Name: ix_monitoring_resources_linked_vm_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitoring_resources_linked_vm_id ON public.monitoring_resources USING btree (linked_vm_id);


--
-- Name: ix_monitoring_resources_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitoring_resources_organization_id ON public.monitoring_resources USING btree (organization_id);


--
-- Name: ix_monitoring_rule_bindings_activation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitoring_rule_bindings_activation_id ON public.monitoring_rule_bindings USING btree (activation_id);


--
-- Name: ix_monitoring_rule_catalogs_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitoring_rule_catalogs_organization_id ON public.monitoring_rule_catalogs USING btree (organization_id);


--
-- Name: ix_monitoring_template_versions_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_monitoring_template_versions_template_id ON public.monitoring_template_versions USING btree (template_id);


--
-- Name: ix_native_incident_alerts_alert_state_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_incident_alerts_alert_state_id ON public.native_incident_alerts USING btree (alert_state_id);


--
-- Name: ix_native_incident_alerts_incident_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_incident_alerts_incident_id ON public.native_incident_alerts USING btree (incident_id);


--
-- Name: ix_native_incident_alerts_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_incident_alerts_organization_id ON public.native_incident_alerts USING btree (organization_id);


--
-- Name: ix_native_incident_details_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_incident_details_organization_id ON public.native_incident_details USING btree (organization_id);


--
-- Name: ix_native_incident_failures_history_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_incident_failures_history_id ON public.native_incident_failures USING btree (history_id);


--
-- Name: ix_native_incident_failures_incident_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_incident_failures_incident_id ON public.native_incident_failures USING btree (incident_id);


--
-- Name: ix_native_incident_failures_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_incident_failures_organization_id ON public.native_incident_failures USING btree (organization_id);


--
-- Name: ix_native_incident_failures_root_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_incident_failures_root_key ON public.native_incident_failures USING btree (root_key);


--
-- Name: ix_native_recovery_assessments_incident_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_recovery_assessments_incident_id ON public.native_recovery_assessments USING btree (incident_id);


--
-- Name: ix_native_recovery_assessments_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_native_recovery_assessments_organization_id ON public.native_recovery_assessments USING btree (organization_id);


--
-- Name: ix_normalized_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_normalized_pending ON public.normalized_telemetry_events USING btree (resource_id, processing_status, observed_at, id);


--
-- Name: ix_normalized_telemetry_events_history_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_normalized_telemetry_events_history_id ON public.normalized_telemetry_events USING btree (history_id);


--
-- Name: ix_normalized_telemetry_events_log_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_normalized_telemetry_events_log_event_id ON public.normalized_telemetry_events USING btree (log_event_id);


--
-- Name: ix_normalized_telemetry_events_observed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_normalized_telemetry_events_observed_at ON public.normalized_telemetry_events USING btree (observed_at);


--
-- Name: ix_normalized_telemetry_events_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_normalized_telemetry_events_organization_id ON public.normalized_telemetry_events USING btree (organization_id);


--
-- Name: ix_normalized_telemetry_events_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_normalized_telemetry_events_resource_id ON public.normalized_telemetry_events USING btree (resource_id);


--
-- Name: ix_notification_destinations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_destinations_organization_id ON public.notification_destinations USING btree (organization_id);


--
-- Name: ix_operational_incidents_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operational_incidents_organization_id ON public.operational_incidents USING btree (organization_id);


--
-- Name: ix_operational_incidents_source_reference; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operational_incidents_source_reference ON public.operational_incidents USING btree (source_reference);


--
-- Name: ix_operator_notes_investigation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operator_notes_investigation_id ON public.operator_notes USING btree (investigation_id);


--
-- Name: ix_organization_memberships_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_memberships_organization_id ON public.organization_memberships USING btree (organization_id);


--
-- Name: ix_organization_memberships_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_memberships_user_id ON public.organization_memberships USING btree (user_id);


--
-- Name: ix_pentaho_alias_attempt; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pentaho_alias_attempt ON public.pentaho_native_aliases USING btree (attempt_id);


--
-- Name: ix_pentaho_instances_vm_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pentaho_instances_vm_id ON public.pentaho_instances USING btree (vm_id);


--
-- Name: ix_pentaho_notice_due; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pentaho_notice_due ON public.pentaho_historical_notices USING btree (status, next_attempt_at);


--
-- Name: ix_pentaho_recovery_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pentaho_recovery_target ON public.pentaho_recovery_links USING btree (recovery_history_id);


--
-- Name: ix_pentaho_review_queue; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pentaho_review_queue ON public.pentaho_evidence_reviews USING btree (organization_id, resource_id, status, created_at);


--
-- Name: ix_pentaho_review_raw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pentaho_review_raw ON public.pentaho_evidence_reviews USING btree (source_evidence_id);


--
-- Name: ix_pentaho_revision_raw_evidence; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pentaho_revision_raw_evidence ON public.pentaho_attempt_revisions USING btree (source_evidence_id);


--
-- Name: ix_pipeline_associations_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_associations_job_id ON public.pipeline_associations USING btree (job_id);


--
-- Name: ix_pipeline_associations_method_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_associations_method_id ON public.pipeline_associations USING btree (method_id);


--
-- Name: ix_pipeline_associations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_associations_organization_id ON public.pipeline_associations USING btree (organization_id);


--
-- Name: ix_pipeline_capabilities_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_capabilities_organization_id ON public.pipeline_capabilities USING btree (organization_id);


--
-- Name: ix_pipeline_connections_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_connections_organization_id ON public.pipeline_connections USING btree (organization_id);


--
-- Name: ix_pipeline_evidence_generation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_evidence_generation ON public.pipeline_evidence USING btree (generation);


--
-- Name: ix_pipeline_evidence_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_evidence_organization_id ON public.pipeline_evidence USING btree (organization_id);


--
-- Name: ix_pipeline_evidence_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_evidence_source_id ON public.pipeline_evidence USING btree (source_id);


--
-- Name: ix_pipeline_holds_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_holds_organization_id ON public.pipeline_holds USING btree (organization_id);


--
-- Name: ix_pipeline_holds_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_holds_source_id ON public.pipeline_holds USING btree (source_id);


--
-- Name: ix_pipeline_integrations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_integrations_organization_id ON public.pipeline_integrations USING btree (organization_id);


--
-- Name: ix_pipeline_jobs_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_jobs_organization_id ON public.pipeline_jobs USING btree (organization_id);


--
-- Name: ix_pipeline_methods_capability_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_methods_capability_id ON public.pipeline_methods USING btree (capability_id);


--
-- Name: ix_pipeline_methods_connection_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_methods_connection_id ON public.pipeline_methods USING btree (connection_id);


--
-- Name: ix_pipeline_methods_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_methods_organization_id ON public.pipeline_methods USING btree (organization_id);


--
-- Name: ix_pipeline_methods_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_methods_source_id ON public.pipeline_methods USING btree (source_id);


--
-- Name: ix_pipeline_operations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_operations_organization_id ON public.pipeline_operations USING btree (organization_id);


--
-- Name: ix_pipeline_sources_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_sources_organization_id ON public.pipeline_sources USING btree (organization_id);


--
-- Name: ix_remote_evidence_org_observed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_remote_evidence_org_observed ON public.remote_probe_evidence USING btree (organization_id, observed_at);


--
-- Name: ix_remote_job_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_remote_job_org_id ON public.remote_probe_jobs USING btree (organization_id);


--
-- Name: ix_remote_job_worker_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_remote_job_worker_state ON public.remote_probe_jobs USING btree (assigned_worker_id, state, planned_for);


--
-- Name: ix_resource_conditions_alert_state_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_conditions_alert_state_id ON public.resource_conditions USING btree (alert_state_id);


--
-- Name: ix_resource_conditions_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_conditions_organization_id ON public.resource_conditions USING btree (organization_id);


--
-- Name: ix_resource_conditions_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_conditions_resource_id ON public.resource_conditions USING btree (resource_id);


--
-- Name: ix_resource_dependencies_depends_on_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_dependencies_depends_on_id ON public.resource_dependencies USING btree (depends_on_id);


--
-- Name: ix_resource_dependencies_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_dependencies_organization_id ON public.resource_dependencies USING btree (organization_id);


--
-- Name: ix_resource_dependencies_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_dependencies_resource_id ON public.resource_dependencies USING btree (resource_id);


--
-- Name: ix_resource_domain_inventory; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_domain_inventory ON public.monitoring_resources USING btree (organization_id, domain, environment, name, id);


--
-- Name: ix_resource_mapping_issues_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_mapping_issues_organization_id ON public.resource_mapping_issues USING btree (organization_id);


--
-- Name: ix_resource_parameter_activations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_parameter_activations_organization_id ON public.resource_parameter_activations USING btree (organization_id);


--
-- Name: ix_resource_parameter_activations_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_parameter_activations_resource_id ON public.resource_parameter_activations USING btree (resource_id);


--
-- Name: ix_resource_parameter_versions_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_parameter_versions_organization_id ON public.resource_parameter_versions USING btree (organization_id);


--
-- Name: ix_resource_parameter_versions_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resource_parameter_versions_resource_id ON public.resource_parameter_versions USING btree (resource_id);


--
-- Name: ix_roles_service_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_roles_service_provider_id ON public.roles USING btree (service_provider_id);


--
-- Name: ix_security_audit_actor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_actor_id ON public.security_audit_events USING btree (actor_id);


--
-- Name: ix_security_audit_occurred; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_occurred ON public.security_audit_events USING btree (occurred_at, id);


--
-- Name: ix_security_audit_occurred_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_occurred_at ON public.security_audit_events USING btree (occurred_at);


--
-- Name: ix_security_audit_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_organization_id ON public.security_audit_events USING btree (organization_id);


--
-- Name: ix_telemetry_agent_signal_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telemetry_agent_signal_time ON public.telemetry_receipts USING btree (agent_id, signal, received_at);


--
-- Name: ix_telemetry_receipts_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telemetry_receipts_agent_id ON public.telemetry_receipts USING btree (agent_id);


--
-- Name: ix_telemetry_receipts_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telemetry_receipts_organization_id ON public.telemetry_receipts USING btree (organization_id);


--
-- Name: ix_template_attachment_data_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_template_attachment_data_source_id ON public.monitoring_template_attachments USING btree (data_source_id);


--
-- Name: ix_template_attachment_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_template_attachment_template_id ON public.monitoring_template_attachments USING btree (template_id);


--
-- Name: ix_trace_spans_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_trace_spans_agent_id ON public.trace_spans USING btree (agent_id);


--
-- Name: ix_trace_spans_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_trace_spans_organization_id ON public.trace_spans USING btree (organization_id);


--
-- Name: ix_user_role_assignments_role_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_role_assignments_role_id ON public.user_role_assignments USING btree (role_id);


--
-- Name: ix_user_role_assignments_service_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_role_assignments_service_provider_id ON public.user_role_assignments USING btree (service_provider_id);


--
-- Name: ix_user_role_assignments_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_role_assignments_user_id ON public.user_role_assignments USING btree (user_id);


--
-- Name: ix_users_service_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_service_provider_id ON public.users USING btree (service_provider_id);


--
-- Name: ix_vms_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_vms_organization_id ON public.vms USING btree (organization_id);


--
-- Name: ix_worker_identities_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_worker_identities_organization_id ON public.worker_identities USING btree (organization_id);


--
-- Name: uq_alert_states_open_rule; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_alert_states_open_rule ON public.alert_states USING btree (alert_rule_id) WHERE ((status)::text = 'OPEN'::text);


--
-- Name: uq_current_parameter_activation; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_current_parameter_activation ON public.resource_parameter_activations USING btree (resource_id) WHERE (effective_to IS NULL);


--
-- Name: uq_department_name_ci; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_department_name_ci ON public.departments USING btree (service_provider_id, lower((name)::text));


--
-- Name: uq_dependency_current; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_dependency_current ON public.resource_dependencies USING btree (resource_id, depends_on_id, relationship_type, service_identity) WHERE (valid_to IS NULL);


--
-- Name: uq_etl_job_provider_execution; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_etl_job_provider_execution ON public.job_order_histories USING btree (job_order_id, provider_execution_id);


--
-- Name: uq_grant_department; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_grant_department ON public.customer_access_grants USING btree (department_id, organization_id, role_id) WHERE (department_id IS NOT NULL);


--
-- Name: uq_grant_employee; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_grant_employee ON public.customer_access_grants USING btree (user_id, organization_id, role_id) NULLS NOT DISTINCT WHERE (user_id IS NOT NULL);


--
-- Name: uq_parameter_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_parameter_active ON public.resource_parameter_versions USING btree (resource_id) WHERE ((status)::text = 'ACTIVE'::text);


--
-- Name: uq_role_name_ci; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_role_name_ci ON public.roles USING btree (service_provider_id, lower((name)::text));


--
-- Name: uq_saas_job_order_identity; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_saas_job_order_identity ON public.job_orders USING btree (organization_id, name, environment) WHERE (vm_id IS NULL);


--
-- Name: uq_step_external_attempt; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_step_external_attempt ON public.job_step_executions USING btree (history_id, external_step_id, attempt) WHERE (external_step_id IS NOT NULL);


--
-- Name: access_boundary_decisions access_boundary_audit_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER access_boundary_audit_immutable BEFORE DELETE OR UPDATE ON public.access_boundary_decisions FOR EACH ROW EXECUTE FUNCTION public.access_boundary_audit_guard();


--
-- Name: customer_access_grants immutable_access_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON public.customer_access_grants FOR EACH ROW EXECUTE FUNCTION public.protect_access_identity();


--
-- Name: department_memberships immutable_access_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON public.department_memberships FOR EACH ROW EXECUTE FUNCTION public.protect_access_identity();


--
-- Name: department_role_assignments immutable_access_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON public.department_role_assignments FOR EACH ROW EXECUTE FUNCTION public.protect_access_identity();


--
-- Name: departments immutable_access_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON public.departments FOR EACH ROW EXECUTE FUNCTION public.protect_access_identity();


--
-- Name: roles immutable_access_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON public.roles FOR EACH ROW EXECUTE FUNCTION public.protect_access_identity();


--
-- Name: service_providers immutable_access_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON public.service_providers FOR EACH ROW EXECUTE FUNCTION public.protect_access_identity();


--
-- Name: user_role_assignments immutable_access_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON public.user_role_assignments FOR EACH ROW EXECUTE FUNCTION public.protect_access_identity();


--
-- Name: users immutable_access_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.protect_access_identity();


--
-- Name: kubernetes_cluster_association_decisions k8s_association_decision_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER k8s_association_decision_immutable BEFORE DELETE OR UPDATE ON public.kubernetes_cluster_association_decisions FOR EACH ROW EXECUTE FUNCTION public.k8s_association_decision_guard();


--
-- Name: kubernetes_cluster_associations k8s_association_revision_valid; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER k8s_association_revision_valid BEFORE DELETE OR UPDATE ON public.kubernetes_cluster_associations FOR EACH ROW EXECUTE FUNCTION public.k8s_association_revision_guard();


--
-- Name: kubernetes_clusters k8s_cluster_identity_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER k8s_cluster_identity_immutable BEFORE DELETE OR UPDATE ON public.kubernetes_clusters FOR EACH ROW EXECUTE FUNCTION public.k8s_cluster_identity_guard();


--
-- Name: native_incident_failures native_recovery_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER native_recovery_immutable BEFORE DELETE OR UPDATE ON public.native_incident_failures FOR EACH ROW EXECUTE FUNCTION public.native_recovery_evidence_guard();


--
-- Name: native_recovery_assessments native_recovery_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER native_recovery_immutable BEFORE DELETE OR UPDATE ON public.native_recovery_assessments FOR EACH ROW EXECUTE FUNCTION public.native_recovery_evidence_guard();


--
-- Name: security_audit_events opscontrol_audit_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER opscontrol_audit_append_only BEFORE DELETE OR UPDATE ON public.security_audit_events FOR EACH ROW EXECUTE FUNCTION public.opscontrol_reject_audit_mutation();


--
-- Name: incident_activities opscontrol_incident_activity_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER opscontrol_incident_activity_append_only BEFORE DELETE OR UPDATE ON public.incident_activities FOR EACH ROW EXECUTE FUNCTION public.opscontrol_incident_activity_guard();


--
-- Name: resource_parameter_versions parameter_version_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER parameter_version_immutable BEFORE DELETE OR UPDATE ON public.resource_parameter_versions FOR EACH ROW EXECUTE FUNCTION public.opscontrol_parameter_immutable();


--
-- Name: pentaho_execution_attempts pentaho_attempt_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_attempt_identity BEFORE DELETE OR UPDATE ON public.pentaho_execution_attempts FOR EACH ROW EXECUTE FUNCTION public.pentaho_attempt_guard();


--
-- Name: pentaho_attempt_revisions pentaho_attempt_revisions_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_attempt_revisions_immutable BEFORE DELETE OR UPDATE ON public.pentaho_attempt_revisions FOR EACH ROW EXECUTE FUNCTION public.pentaho_append_only();


--
-- Name: normalized_telemetry_events pentaho_event_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_event_immutable BEFORE DELETE OR UPDATE ON public.normalized_telemetry_events FOR EACH ROW EXECUTE FUNCTION public.pentaho_event_guard();


--
-- Name: pentaho_evidence_decisions pentaho_evidence_decisions_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_evidence_decisions_immutable BEFORE DELETE OR UPDATE ON public.pentaho_evidence_decisions FOR EACH ROW EXECUTE FUNCTION public.pentaho_append_only();


--
-- Name: pentaho_evidence_reviews pentaho_evidence_review_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_evidence_review_identity BEFORE DELETE OR UPDATE ON public.pentaho_evidence_reviews FOR EACH ROW EXECUTE FUNCTION public.pentaho_review_guard();


--
-- Name: job_order_histories pentaho_history_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_history_identity BEFORE DELETE OR UPDATE ON public.job_order_histories FOR EACH ROW EXECUTE FUNCTION public.pentaho_history_guard();


--
-- Name: in_app_notifications pentaho_inbox_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_inbox_immutable BEFORE DELETE OR UPDATE ON public.in_app_notifications FOR EACH ROW EXECUTE FUNCTION public.pentaho_inbox_guard();


--
-- Name: pentaho_native_aliases pentaho_native_aliases_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_native_aliases_immutable BEFORE DELETE OR UPDATE ON public.pentaho_native_aliases FOR EACH ROW EXECUTE FUNCTION public.pentaho_append_only();


--
-- Name: pentaho_historical_notices pentaho_notice_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_notice_immutable BEFORE DELETE OR UPDATE ON public.pentaho_historical_notices FOR EACH ROW EXECUTE FUNCTION public.pentaho_notice_guard();


--
-- Name: expected_execution_windows pentaho_occurrence_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_occurrence_immutable BEFORE DELETE OR UPDATE ON public.expected_execution_windows FOR EACH ROW EXECUTE FUNCTION public.pentaho_occurrence_guard();


--
-- Name: pentaho_recovery_decisions pentaho_recovery_decisions_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pentaho_recovery_decisions_immutable BEFORE DELETE OR UPDATE ON public.pentaho_recovery_decisions FOR EACH ROW EXECUTE FUNCTION public.pentaho_append_only();


--
-- Name: attribute_registry_versions registry_version_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registry_version_immutable BEFORE DELETE OR UPDATE ON public.attribute_registry_versions FOR EACH ROW EXECUTE FUNCTION public.opscontrol_registry_immutable();


--
-- Name: monitoring_resources resource_identity_guard; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER resource_identity_guard BEFORE INSERT OR UPDATE ON public.monitoring_resources FOR EACH ROW EXECUTE FUNCTION public.opscontrol_resource_identity_guard();


--
-- Name: collector_runtime_states runtime_scope_guard; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER runtime_scope_guard BEFORE INSERT OR UPDATE ON public.collector_runtime_states FOR EACH ROW EXECUTE FUNCTION public.opscontrol_runtime_scope_guard();


--
-- Name: department_memberships trg_single_department; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_single_department BEFORE INSERT OR UPDATE ON public.department_memberships FOR EACH ROW EXECUTE FUNCTION public.opscontrol_single_department();


--
-- Name: access_boundaries access_boundaries_service_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_boundaries
    ADD CONSTRAINT access_boundaries_service_provider_id_fkey FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id) ON DELETE RESTRICT;


--
-- Name: access_boundary_decisions access_boundary_decisions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_boundary_decisions
    ADD CONSTRAINT access_boundary_decisions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: access_boundary_decisions access_boundary_decisions_boundary_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_boundary_decisions
    ADD CONSTRAINT access_boundary_decisions_boundary_id_fkey FOREIGN KEY (boundary_id) REFERENCES public.access_boundaries(id) ON DELETE RESTRICT;


--
-- Name: access_sessions access_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_sessions
    ADD CONSTRAINT access_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: agent_deployments agent_deployments_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_deployments
    ADD CONSTRAINT agent_deployments_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: agent_deployments agent_deployments_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_deployments
    ADD CONSTRAINT agent_deployments_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.managed_agents(id);


--
-- Name: agent_deployments agent_deployments_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_deployments
    ADD CONSTRAINT agent_deployments_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: agent_registrations agent_registrations_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_registrations
    ADD CONSTRAINT agent_registrations_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: agent_registrations agent_registrations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_registrations
    ADD CONSTRAINT agent_registrations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: alert_incident_events alert_incident_events_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_incident_events
    ADD CONSTRAINT alert_incident_events_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.job_order_histories(id);


--
-- Name: alert_notification_deliveries alert_notification_deliveries_alert_state_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_notification_deliveries
    ADD CONSTRAINT alert_notification_deliveries_alert_state_id_fkey FOREIGN KEY (alert_state_id) REFERENCES public.alert_states(id);


--
-- Name: alert_rules alert_rules_metric_definition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_rules
    ADD CONSTRAINT alert_rules_metric_definition_id_fkey FOREIGN KEY (metric_definition_id) REFERENCES public.metric_definitions(id);


--
-- Name: alert_rules alert_rules_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_rules
    ADD CONSTRAINT alert_rules_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: alert_states alert_states_acknowledged_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_states
    ADD CONSTRAINT alert_states_acknowledged_by_fkey FOREIGN KEY (acknowledged_by) REFERENCES public.users(id);


--
-- Name: alert_states alert_states_alert_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_states
    ADD CONSTRAINT alert_states_alert_rule_id_fkey FOREIGN KEY (alert_rule_id) REFERENCES public.alert_rules(id);


--
-- Name: alert_states alert_states_metric_definition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_states
    ADD CONSTRAINT alert_states_metric_definition_id_fkey FOREIGN KEY (metric_definition_id) REFERENCES public.metric_definitions(id);


--
-- Name: alert_states alert_states_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_states
    ADD CONSTRAINT alert_states_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: applications applications_vm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_vm_id_fkey FOREIGN KEY (vm_id) REFERENCES public.vms(id);


--
-- Name: collector_config_versions collector_config_versions_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_config_versions
    ADD CONSTRAINT collector_config_versions_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: collector_config_versions collector_config_versions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_config_versions
    ADD CONSTRAINT collector_config_versions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: collector_methods collector_methods_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_methods
    ADD CONSTRAINT collector_methods_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: collector_methods collector_methods_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_methods
    ADD CONSTRAINT collector_methods_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: collector_runs collector_runs_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_runs
    ADD CONSTRAINT collector_runs_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: collector_runtime_states collector_runtime_states_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_runtime_states
    ADD CONSTRAINT collector_runtime_states_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: collector_runtime_states collector_runtime_states_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collector_runtime_states
    ADD CONSTRAINT collector_runtime_states_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: collectors collectors_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collectors
    ADD CONSTRAINT collectors_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id);


--
-- Name: collectors collectors_remote_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collectors
    ADD CONSTRAINT collectors_remote_worker_id_fkey FOREIGN KEY (remote_worker_id) REFERENCES public.worker_identities(id) ON DELETE SET NULL;


--
-- Name: correlation_evidence correlation_evidence_correlation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correlation_evidence
    ADD CONSTRAINT correlation_evidence_correlation_id_fkey FOREIGN KEY (correlation_id) REFERENCES public.correlation_records(id);


--
-- Name: correlation_records correlation_records_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correlation_records
    ADD CONSTRAINT correlation_records_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.job_order_histories(id);


--
-- Name: correlation_records correlation_records_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correlation_records
    ADD CONSTRAINT correlation_records_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: customer_access_grants customer_access_grants_legacy_membership_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT customer_access_grants_legacy_membership_id_fkey FOREIGN KEY (legacy_membership_id) REFERENCES public.organization_memberships(id) ON DELETE CASCADE;


--
-- Name: customer_access_grants customer_access_grants_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT customer_access_grants_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: customer_access_grants customer_access_grants_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT customer_access_grants_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE RESTRICT;


--
-- Name: customer_access_grants customer_access_grants_service_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT customer_access_grants_service_provider_id_fkey FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id) ON DELETE RESTRICT;


--
-- Name: data_sources data_sources_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: department_memberships department_memberships_service_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_memberships
    ADD CONSTRAINT department_memberships_service_provider_id_fkey FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id) ON DELETE RESTRICT;


--
-- Name: department_role_assignments department_role_assignments_service_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_role_assignments
    ADD CONSTRAINT department_role_assignments_service_provider_id_fkey FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id) ON DELETE RESTRICT;


--
-- Name: departments departments_service_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_service_provider_id_fkey FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id) ON DELETE RESTRICT;


--
-- Name: event_correlation_groups event_correlation_groups_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_groups
    ADD CONSTRAINT event_correlation_groups_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: event_correlation_members event_correlation_members_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_members
    ADD CONSTRAINT event_correlation_members_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: event_correlation_members event_correlation_members_relationship_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_members
    ADD CONSTRAINT event_correlation_members_relationship_id_fkey FOREIGN KEY (relationship_id) REFERENCES public.resource_dependencies(id);


--
-- Name: expected_execution_windows expected_execution_windows_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expected_execution_windows
    ADD CONSTRAINT expected_execution_windows_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.job_order_histories(id);


--
-- Name: expected_execution_windows expected_execution_windows_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expected_execution_windows
    ADD CONSTRAINT expected_execution_windows_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_associations fk_association_job_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_associations
    ADD CONSTRAINT fk_association_job_scope FOREIGN KEY (organization_id, job_id) REFERENCES public.pipeline_jobs(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_associations fk_association_method_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_associations
    ADD CONSTRAINT fk_association_method_scope FOREIGN KEY (organization_id, method_id) REFERENCES public.pipeline_methods(organization_id, id) ON DELETE RESTRICT;


--
-- Name: access_boundaries fk_boundary_department; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_boundaries
    ADD CONSTRAINT fk_boundary_department FOREIGN KEY (department_id, service_provider_id) REFERENCES public.departments(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: access_boundaries fk_boundary_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_boundaries
    ADD CONSTRAINT fk_boundary_user FOREIGN KEY (user_id, service_provider_id) REFERENCES public.users(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: resource_conditions fk_condition_resource_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_conditions
    ADD CONSTRAINT fk_condition_resource_scope FOREIGN KEY (organization_id, resource_id) REFERENCES public.monitoring_resources(organization_id, id);


--
-- Name: departments fk_department_manager_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT fk_department_manager_provider FOREIGN KEY (manager_id, service_provider_id) REFERENCES public.users(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: department_role_assignments fk_department_role_owner; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_role_assignments
    ADD CONSTRAINT fk_department_role_owner FOREIGN KEY (department_id, service_provider_id) REFERENCES public.departments(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: department_role_assignments fk_department_role_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_role_assignments
    ADD CONSTRAINT fk_department_role_provider FOREIGN KEY (role_id, service_provider_id) REFERENCES public.roles(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: resource_dependencies fk_dependency_parent_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_dependencies
    ADD CONSTRAINT fk_dependency_parent_scope FOREIGN KEY (organization_id, depends_on_id) REFERENCES public.monitoring_resources(organization_id, id);


--
-- Name: resource_dependencies fk_dependency_resource_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_dependencies
    ADD CONSTRAINT fk_dependency_resource_scope FOREIGN KEY (organization_id, resource_id) REFERENCES public.monitoring_resources(organization_id, id);


--
-- Name: resource_drafts fk_draft_owner_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_drafts
    ADD CONSTRAINT fk_draft_owner_provider FOREIGN KEY (owner_id, service_provider_id) REFERENCES public.users(id, service_provider_id);


--
-- Name: user_role_assignments fk_employee_role_owner; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role_assignments
    ADD CONSTRAINT fk_employee_role_owner FOREIGN KEY (user_id, service_provider_id) REFERENCES public.users(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: user_role_assignments fk_employee_role_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role_assignments
    ADD CONSTRAINT fk_employee_role_provider FOREIGN KEY (role_id, service_provider_id) REFERENCES public.roles(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: customer_access_grants fk_grant_department_assignment; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT fk_grant_department_assignment FOREIGN KEY (department_id, role_id) REFERENCES public.department_role_assignments(department_id, role_id) ON DELETE CASCADE;


--
-- Name: customer_access_grants fk_grant_department_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT fk_grant_department_provider FOREIGN KEY (department_id, service_provider_id) REFERENCES public.departments(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: customer_access_grants fk_grant_employee_assignment; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT fk_grant_employee_assignment FOREIGN KEY (user_id, role_id) REFERENCES public.user_role_assignments(user_id, role_id) ON DELETE CASCADE;


--
-- Name: customer_access_grants fk_grant_employee_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT fk_grant_employee_provider FOREIGN KEY (user_id, service_provider_id) REFERENCES public.users(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: customer_access_grants fk_grant_role_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grants
    ADD CONSTRAINT fk_grant_role_provider FOREIGN KEY (role_id, service_provider_id) REFERENCES public.roles(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: in_app_notifications fk_in_app_historical_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notifications
    ADD CONSTRAINT fk_in_app_historical_scope FOREIGN KEY (organization_id, historical_notice_id) REFERENCES public.pentaho_historical_notices(organization_id, id) ON DELETE RESTRICT;


--
-- Name: job_orders fk_job_order_host_source; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_orders
    ADD CONSTRAINT fk_job_order_host_source FOREIGN KEY (host_data_source_id) REFERENCES public.data_sources(id);


--
-- Name: event_correlation_members fk_member_condition_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_members
    ADD CONSTRAINT fk_member_condition_scope FOREIGN KEY (organization_id, condition_id) REFERENCES public.resource_conditions(organization_id, id);


--
-- Name: event_correlation_members fk_member_group_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_correlation_members
    ADD CONSTRAINT fk_member_group_scope FOREIGN KEY (organization_id, group_id) REFERENCES public.event_correlation_groups(organization_id, id);


--
-- Name: department_memberships fk_membership_department_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_memberships
    ADD CONSTRAINT fk_membership_department_provider FOREIGN KEY (department_id, service_provider_id) REFERENCES public.departments(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: department_memberships fk_membership_employee_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department_memberships
    ADD CONSTRAINT fk_membership_employee_provider FOREIGN KEY (user_id, service_provider_id) REFERENCES public.users(id, service_provider_id) ON DELETE RESTRICT;


--
-- Name: pipeline_methods fk_method_capability_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_methods
    ADD CONSTRAINT fk_method_capability_id FOREIGN KEY (organization_id, capability_id) REFERENCES public.pipeline_capabilities(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_methods fk_method_connection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_methods
    ADD CONSTRAINT fk_method_connection_id FOREIGN KEY (organization_id, connection_id) REFERENCES public.pipeline_connections(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_methods fk_method_integration_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_methods
    ADD CONSTRAINT fk_method_integration_id FOREIGN KEY (organization_id, integration_id) REFERENCES public.pipeline_integrations(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_methods fk_method_source_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_methods
    ADD CONSTRAINT fk_method_source_id FOREIGN KEY (organization_id, source_id) REFERENCES public.pipeline_sources(organization_id, id) ON DELETE RESTRICT;


--
-- Name: native_incident_alerts fk_native_alert_incident_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_alerts
    ADD CONSTRAINT fk_native_alert_incident_scope FOREIGN KEY (organization_id, incident_id) REFERENCES public.operational_incidents(organization_id, id);


--
-- Name: native_incident_alerts fk_native_alert_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_alerts
    ADD CONSTRAINT fk_native_alert_scope FOREIGN KEY (organization_id, alert_state_id) REFERENCES public.alert_states(organization_id, id);


--
-- Name: native_recovery_assessments fk_native_assessment_incident; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_recovery_assessments
    ADD CONSTRAINT fk_native_assessment_incident FOREIGN KEY (organization_id, incident_id) REFERENCES public.operational_incidents(organization_id, id);


--
-- Name: native_incident_details fk_native_details_incident_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_details
    ADD CONSTRAINT fk_native_details_incident_scope FOREIGN KEY (organization_id, incident_id) REFERENCES public.operational_incidents(organization_id, id);


--
-- Name: native_incident_failures fk_native_failure_event; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_failures
    ADD CONSTRAINT fk_native_failure_event FOREIGN KEY (organization_id, resource_id, event_id) REFERENCES public.normalized_telemetry_events(organization_id, resource_id, id);


--
-- Name: native_incident_failures fk_native_failure_history; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_failures
    ADD CONSTRAINT fk_native_failure_history FOREIGN KEY (organization_id, resource_id, history_id) REFERENCES public.job_order_histories(pentaho_customer_id, pentaho_resource_id, id);


--
-- Name: native_incident_failures fk_native_failure_incident; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_failures
    ADD CONSTRAINT fk_native_failure_incident FOREIGN KEY (organization_id, incident_id) REFERENCES public.operational_incidents(organization_id, id);


--
-- Name: normalized_telemetry_events fk_normalized_resource_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_telemetry_events
    ADD CONSTRAINT fk_normalized_resource_scope FOREIGN KEY (organization_id, resource_id) REFERENCES public.monitoring_resources(organization_id, id);


--
-- Name: resource_parameter_activations fk_parameter_activation_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_activations
    ADD CONSTRAINT fk_parameter_activation_scope FOREIGN KEY (organization_id, resource_id) REFERENCES public.monitoring_resources(organization_id, id);


--
-- Name: resource_parameter_activations fk_parameter_activation_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_activations
    ADD CONSTRAINT fk_parameter_activation_version FOREIGN KEY (resource_id, parameter_version) REFERENCES public.resource_parameter_versions(resource_id, version);


--
-- Name: resource_parameter_versions fk_parameter_resource_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_versions
    ADD CONSTRAINT fk_parameter_resource_scope FOREIGN KEY (organization_id, resource_id) REFERENCES public.monitoring_resources(organization_id, id);


--
-- Name: pentaho_native_aliases fk_pentaho_alias_attempt_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_native_aliases
    ADD CONSTRAINT fk_pentaho_alias_attempt_scope FOREIGN KEY (organization_id, resource_id, history_id, attempt_id) REFERENCES public.pentaho_execution_attempts(organization_id, resource_id, history_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_native_aliases fk_pentaho_alias_history_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_native_aliases
    ADD CONSTRAINT fk_pentaho_alias_history_scope FOREIGN KEY (organization_id, resource_id, history_id) REFERENCES public.job_order_histories(pentaho_customer_id, pentaho_resource_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_execution_attempts fk_pentaho_attempt_history_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_execution_attempts
    ADD CONSTRAINT fk_pentaho_attempt_history_scope FOREIGN KEY (organization_id, resource_id, history_id) REFERENCES public.job_order_histories(pentaho_customer_id, pentaho_resource_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_evidence_decisions fk_pentaho_decision_review; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_decisions
    ADD CONSTRAINT fk_pentaho_decision_review FOREIGN KEY (organization_id, resource_id, review_id) REFERENCES public.pentaho_evidence_reviews(organization_id, resource_id, id) ON DELETE RESTRICT;


--
-- Name: job_order_histories fk_pentaho_history_resource_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_order_histories
    ADD CONSTRAINT fk_pentaho_history_resource_scope FOREIGN KEY (pentaho_customer_id, pentaho_resource_id, job_order_id) REFERENCES public.monitoring_resources(organization_id, id, job_order_id) ON DELETE RESTRICT;


--
-- Name: pentaho_historical_notices fk_pentaho_notice_destination; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_historical_notices
    ADD CONSTRAINT fk_pentaho_notice_destination FOREIGN KEY (organization_id, destination_id) REFERENCES public.notification_destinations(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_historical_notices fk_pentaho_notice_event; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_historical_notices
    ADD CONSTRAINT fk_pentaho_notice_event FOREIGN KEY (organization_id, resource_id, event_id) REFERENCES public.normalized_telemetry_events(organization_id, resource_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_historical_notices fk_pentaho_notice_history; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_historical_notices
    ADD CONSTRAINT fk_pentaho_notice_history FOREIGN KEY (organization_id, resource_id, history_id) REFERENCES public.job_order_histories(pentaho_customer_id, pentaho_resource_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_recovery_decisions fk_pentaho_recovery_decision_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_decisions
    ADD CONSTRAINT fk_pentaho_recovery_decision_scope FOREIGN KEY (organization_id, link_id) REFERENCES public.pentaho_recovery_links(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_recovery_links fk_pentaho_recovery_failed_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_links
    ADD CONSTRAINT fk_pentaho_recovery_failed_scope FOREIGN KEY (organization_id, failed_history_id) REFERENCES public.job_order_histories(pentaho_customer_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_recovery_links fk_pentaho_recovery_run_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_links
    ADD CONSTRAINT fk_pentaho_recovery_run_scope FOREIGN KEY (organization_id, recovery_history_id) REFERENCES public.job_order_histories(pentaho_customer_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_evidence_reviews fk_pentaho_review_event; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_reviews
    ADD CONSTRAINT fk_pentaho_review_event FOREIGN KEY (organization_id, resource_id, event_id) REFERENCES public.normalized_telemetry_events(organization_id, resource_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_evidence_reviews fk_pentaho_review_history; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_reviews
    ADD CONSTRAINT fk_pentaho_review_history FOREIGN KEY (job_order_id, history_id) REFERENCES public.job_order_histories(job_order_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_evidence_reviews fk_pentaho_review_raw; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_reviews
    ADD CONSTRAINT fk_pentaho_review_raw FOREIGN KEY (organization_id, source_evidence_id) REFERENCES public.pipeline_evidence(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_evidence_reviews fk_pentaho_review_resource; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_reviews
    ADD CONSTRAINT fk_pentaho_review_resource FOREIGN KEY (organization_id, resource_id, job_order_id) REFERENCES public.monitoring_resources(organization_id, id, job_order_id) ON DELETE RESTRICT;


--
-- Name: pentaho_attempt_revisions fk_pentaho_revision_attempt_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT fk_pentaho_revision_attempt_scope FOREIGN KEY (organization_id, resource_id, history_id, attempt_id) REFERENCES public.pentaho_execution_attempts(organization_id, resource_id, history_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_attempt_revisions fk_pentaho_revision_event_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT fk_pentaho_revision_event_scope FOREIGN KEY (organization_id, resource_id, event_id) REFERENCES public.normalized_telemetry_events(organization_id, resource_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_attempt_revisions fk_pentaho_revision_history_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT fk_pentaho_revision_history_scope FOREIGN KEY (organization_id, resource_id, history_id) REFERENCES public.job_order_histories(pentaho_customer_id, pentaho_resource_id, id) ON DELETE RESTRICT;


--
-- Name: pentaho_attempt_revisions fk_pentaho_revision_raw_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT fk_pentaho_revision_raw_scope FOREIGN KEY (organization_id, source_evidence_id) REFERENCES public.pipeline_evidence(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_capabilities fk_pipeline_capability_proof_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_capabilities
    ADD CONSTRAINT fk_pipeline_capability_proof_scope FOREIGN KEY (organization_id, verification_evidence_id) REFERENCES public.pipeline_evidence(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_capabilities fk_pipeline_capability_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_capabilities
    ADD CONSTRAINT fk_pipeline_capability_scope FOREIGN KEY (organization_id, integration_id) REFERENCES public.pipeline_integrations(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_connections fk_pipeline_connection_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_connections
    ADD CONSTRAINT fk_pipeline_connection_scope FOREIGN KEY (organization_id, integration_id) REFERENCES public.pipeline_integrations(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_evidence fk_pipeline_evidence_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_evidence
    ADD CONSTRAINT fk_pipeline_evidence_scope FOREIGN KEY (organization_id, source_id) REFERENCES public.pipeline_sources(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_holds fk_pipeline_hold_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_holds
    ADD CONSTRAINT fk_pipeline_hold_scope FOREIGN KEY (organization_id, source_id) REFERENCES public.pipeline_sources(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_jobs fk_pipeline_job_resource_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_jobs
    ADD CONSTRAINT fk_pipeline_job_resource_scope FOREIGN KEY (organization_id, resource_id) REFERENCES public.monitoring_resources(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_jobs fk_pipeline_job_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_jobs
    ADD CONSTRAINT fk_pipeline_job_scope FOREIGN KEY (organization_id, integration_id) REFERENCES public.pipeline_integrations(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_operations fk_pipeline_operation_integration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_operations
    ADD CONSTRAINT fk_pipeline_operation_integration FOREIGN KEY (organization_id, integration_id) REFERENCES public.pipeline_integrations(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_operations fk_pipeline_operation_source; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_operations
    ADD CONSTRAINT fk_pipeline_operation_source FOREIGN KEY (organization_id, source_id) REFERENCES public.pipeline_sources(organization_id, id) ON DELETE RESTRICT;


--
-- Name: pipeline_integrations fk_pipeline_vm_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_integrations
    ADD CONSTRAINT fk_pipeline_vm_scope FOREIGN KEY (organization_id, vm_resource_id) REFERENCES public.monitoring_resources(organization_id, id) ON DELETE RESTRICT;


--
-- Name: expected_execution_windows fk_schedule_resource_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expected_execution_windows
    ADD CONSTRAINT fk_schedule_resource_scope FOREIGN KEY (organization_id, resource_id) REFERENCES public.monitoring_resources(organization_id, id);


--
-- Name: users fk_user_service_provider; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_user_service_provider FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id) ON DELETE RESTRICT;


--
-- Name: in_app_notifications in_app_notifications_delivery_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notifications
    ADD CONSTRAINT in_app_notifications_delivery_id_fkey FOREIGN KEY (delivery_id) REFERENCES public.alert_notification_deliveries(id) ON DELETE RESTRICT;


--
-- Name: in_app_notifications in_app_notifications_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notifications
    ADD CONSTRAINT in_app_notifications_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: in_app_notifications in_app_notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notifications
    ADD CONSTRAINT in_app_notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: incident_activities incident_activities_incident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.incident_activities
    ADD CONSTRAINT incident_activities_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES public.operational_incidents(id);


--
-- Name: incident_activities incident_activities_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.incident_activities
    ADD CONSTRAINT incident_activities_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: infrastructure_evidence infrastructure_evidence_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.infrastructure_evidence
    ADD CONSTRAINT infrastructure_evidence_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: infrastructure_evidence infrastructure_evidence_collector_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.infrastructure_evidence
    ADD CONSTRAINT infrastructure_evidence_collector_run_id_fkey FOREIGN KEY (collector_run_id) REFERENCES public.collector_runs(id) ON DELETE CASCADE;


--
-- Name: infrastructure_evidence infrastructure_evidence_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.infrastructure_evidence
    ADD CONSTRAINT infrastructure_evidence_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id);


--
-- Name: infrastructure_evidence infrastructure_evidence_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.infrastructure_evidence
    ADD CONSTRAINT infrastructure_evidence_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: investigation_transitions investigation_transitions_investigation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigation_transitions
    ADD CONSTRAINT investigation_transitions_investigation_id_fkey FOREIGN KEY (investigation_id) REFERENCES public.investigations(id);


--
-- Name: investigations investigations_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.investigations
    ADD CONSTRAINT investigations_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.job_order_histories(id);


--
-- Name: job_order_histories job_order_histories_job_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_order_histories
    ADD CONSTRAINT job_order_histories_job_order_id_fkey FOREIGN KEY (job_order_id) REFERENCES public.job_orders(id);


--
-- Name: job_orders job_orders_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_orders
    ADD CONSTRAINT job_orders_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: job_orders job_orders_pentaho_instance_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_orders
    ADD CONSTRAINT job_orders_pentaho_instance_id_fkey FOREIGN KEY (pentaho_instance_id) REFERENCES public.pentaho_instances(id);


--
-- Name: job_orders job_orders_vm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_orders
    ADD CONSTRAINT job_orders_vm_id_fkey FOREIGN KEY (vm_id) REFERENCES public.vms(id);


--
-- Name: job_step_executions job_step_executions_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_step_executions
    ADD CONSTRAINT job_step_executions_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.job_order_histories(id);


--
-- Name: kubernetes_cluster_association_decisions kubernetes_cluster_association_decisions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_cluster_association_decisions
    ADD CONSTRAINT kubernetes_cluster_association_decisions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: kubernetes_cluster_association_decisions kubernetes_cluster_association_decisions_association_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_cluster_association_decisions
    ADD CONSTRAINT kubernetes_cluster_association_decisions_association_id_fkey FOREIGN KEY (association_id) REFERENCES public.kubernetes_cluster_associations(id) ON DELETE RESTRICT;


--
-- Name: kubernetes_cluster_associations kubernetes_cluster_associations_cluster_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_cluster_associations
    ADD CONSTRAINT kubernetes_cluster_associations_cluster_id_fkey FOREIGN KEY (cluster_id) REFERENCES public.kubernetes_clusters(id) ON DELETE RESTRICT;


--
-- Name: kubernetes_cluster_associations kubernetes_cluster_associations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kubernetes_cluster_associations
    ADD CONSTRAINT kubernetes_cluster_associations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: log_events log_events_log_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_events
    ADD CONSTRAINT log_events_log_source_id_fkey FOREIGN KEY (log_source_id) REFERENCES public.log_sources(id);


--
-- Name: log_events log_events_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_events
    ADD CONSTRAINT log_events_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: log_sources log_sources_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_sources
    ADD CONSTRAINT log_sources_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: log_sources log_sources_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_sources
    ADD CONSTRAINT log_sources_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id);


--
-- Name: log_sources log_sources_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_sources
    ADD CONSTRAINT log_sources_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: managed_agents managed_agents_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managed_agents
    ADD CONSTRAINT managed_agents_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: managed_agents managed_agents_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managed_agents
    ADD CONSTRAINT managed_agents_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: managed_agents managed_agents_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managed_agents
    ADD CONSTRAINT managed_agents_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.worker_identities(id);


--
-- Name: metric_definitions metric_definitions_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_definitions
    ADD CONSTRAINT metric_definitions_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: metric_definitions metric_definitions_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_definitions
    ADD CONSTRAINT metric_definitions_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id);


--
-- Name: metric_definitions metric_definitions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_definitions
    ADD CONSTRAINT metric_definitions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: metric_samples metric_samples_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_samples
    ADD CONSTRAINT metric_samples_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id);


--
-- Name: metric_samples metric_samples_collector_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_samples
    ADD CONSTRAINT metric_samples_collector_run_id_fkey FOREIGN KEY (collector_run_id) REFERENCES public.collector_runs(id);


--
-- Name: metric_samples metric_samples_metric_definition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_samples
    ADD CONSTRAINT metric_samples_metric_definition_id_fkey FOREIGN KEY (metric_definition_id) REFERENCES public.metric_definitions(id);


--
-- Name: metric_samples metric_samples_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_samples
    ADD CONSTRAINT metric_samples_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: monitoring_activations monitoring_activations_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_activations
    ADD CONSTRAINT monitoring_activations_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id) ON DELETE SET NULL;


--
-- Name: monitoring_activations monitoring_activations_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_activations
    ADD CONSTRAINT monitoring_activations_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id) ON DELETE CASCADE;


--
-- Name: monitoring_activations monitoring_activations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_activations
    ADD CONSTRAINT monitoring_activations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: monitoring_resources monitoring_resources_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id);


--
-- Name: monitoring_resources monitoring_resources_job_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_job_order_id_fkey FOREIGN KEY (job_order_id) REFERENCES public.job_orders(id);


--
-- Name: monitoring_resources monitoring_resources_linked_vm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_linked_vm_id_fkey FOREIGN KEY (linked_vm_id) REFERENCES public.vms(id);


--
-- Name: monitoring_resources monitoring_resources_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: monitoring_resources monitoring_resources_primary_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_primary_collector_id_fkey FOREIGN KEY (primary_collector_id) REFERENCES public.collectors(id);


--
-- Name: monitoring_resources monitoring_resources_vm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_resources
    ADD CONSTRAINT monitoring_resources_vm_id_fkey FOREIGN KEY (vm_id) REFERENCES public.vms(id);


--
-- Name: monitoring_rule_bindings monitoring_rule_bindings_activation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_bindings
    ADD CONSTRAINT monitoring_rule_bindings_activation_id_fkey FOREIGN KEY (activation_id) REFERENCES public.monitoring_activations(id) ON DELETE CASCADE;


--
-- Name: monitoring_rule_bindings monitoring_rule_bindings_rule_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_bindings
    ADD CONSTRAINT monitoring_rule_bindings_rule_version_id_fkey FOREIGN KEY (rule_version_id) REFERENCES public.monitoring_rule_versions(id);


--
-- Name: monitoring_rule_catalogs monitoring_rule_catalogs_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_catalogs
    ADD CONSTRAINT monitoring_rule_catalogs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: monitoring_rule_versions monitoring_rule_versions_catalog_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_rule_versions
    ADD CONSTRAINT monitoring_rule_versions_catalog_id_fkey FOREIGN KEY (catalog_id) REFERENCES public.monitoring_rule_catalogs(id) ON DELETE CASCADE;


--
-- Name: monitoring_template_attachments monitoring_template_attachments_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_template_attachments
    ADD CONSTRAINT monitoring_template_attachments_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id) ON DELETE CASCADE;


--
-- Name: monitoring_template_attachments monitoring_template_attachments_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_template_attachments
    ADD CONSTRAINT monitoring_template_attachments_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.monitoring_templates(id) ON DELETE RESTRICT;


--
-- Name: monitoring_template_versions monitoring_template_versions_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monitoring_template_versions
    ADD CONSTRAINT monitoring_template_versions_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.monitoring_templates(id) ON DELETE CASCADE;


--
-- Name: native_incident_alerts native_incident_alerts_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_alerts
    ADD CONSTRAINT native_incident_alerts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: native_incident_details native_incident_details_assigned_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_details
    ADD CONSTRAINT native_incident_details_assigned_user_id_fkey FOREIGN KEY (assigned_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: native_incident_details native_incident_details_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_details
    ADD CONSTRAINT native_incident_details_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: native_incident_failures native_incident_failures_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_incident_failures
    ADD CONSTRAINT native_incident_failures_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: native_recovery_assessments native_recovery_assessments_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_recovery_assessments
    ADD CONSTRAINT native_recovery_assessments_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: native_recovery_assessments native_recovery_assessments_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.native_recovery_assessments
    ADD CONSTRAINT native_recovery_assessments_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: normalized_telemetry_events normalized_telemetry_events_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_telemetry_events
    ADD CONSTRAINT normalized_telemetry_events_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.job_order_histories(id);


--
-- Name: normalized_telemetry_events normalized_telemetry_events_log_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_telemetry_events
    ADD CONSTRAINT normalized_telemetry_events_log_event_id_fkey FOREIGN KEY (log_event_id) REFERENCES public.log_events(id);


--
-- Name: normalized_telemetry_events normalized_telemetry_events_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_telemetry_events
    ADD CONSTRAINT normalized_telemetry_events_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: notification_destinations notification_destinations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_destinations
    ADD CONSTRAINT notification_destinations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: operational_incidents operational_incidents_alert_state_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operational_incidents
    ADD CONSTRAINT operational_incidents_alert_state_id_fkey FOREIGN KEY (alert_state_id) REFERENCES public.alert_states(id);


--
-- Name: operational_incidents operational_incidents_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operational_incidents
    ADD CONSTRAINT operational_incidents_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id);


--
-- Name: operational_incidents operational_incidents_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operational_incidents
    ADD CONSTRAINT operational_incidents_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.job_order_histories(id);


--
-- Name: operational_incidents operational_incidents_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operational_incidents
    ADD CONSTRAINT operational_incidents_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: operator_notes operator_notes_investigation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operator_notes
    ADD CONSTRAINT operator_notes_investigation_id_fkey FOREIGN KEY (investigation_id) REFERENCES public.investigations(id);


--
-- Name: organization_memberships organization_memberships_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_memberships
    ADD CONSTRAINT organization_memberships_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: organization_memberships organization_memberships_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_memberships
    ADD CONSTRAINT organization_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: pentaho_attempt_revisions pentaho_attempt_revisions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_attempt_revisions
    ADD CONSTRAINT pentaho_attempt_revisions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pentaho_evidence_decisions pentaho_evidence_decisions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_decisions
    ADD CONSTRAINT pentaho_evidence_decisions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: pentaho_evidence_decisions pentaho_evidence_decisions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_decisions
    ADD CONSTRAINT pentaho_evidence_decisions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pentaho_evidence_reviews pentaho_evidence_reviews_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_evidence_reviews
    ADD CONSTRAINT pentaho_evidence_reviews_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pentaho_execution_attempts pentaho_execution_attempts_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_execution_attempts
    ADD CONSTRAINT pentaho_execution_attempts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pentaho_historical_notices pentaho_historical_notices_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_historical_notices
    ADD CONSTRAINT pentaho_historical_notices_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pentaho_instances pentaho_instances_vm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_instances
    ADD CONSTRAINT pentaho_instances_vm_id_fkey FOREIGN KEY (vm_id) REFERENCES public.vms(id);


--
-- Name: pentaho_native_aliases pentaho_native_aliases_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_native_aliases
    ADD CONSTRAINT pentaho_native_aliases_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pentaho_recovery_decisions pentaho_recovery_decisions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_decisions
    ADD CONSTRAINT pentaho_recovery_decisions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: pentaho_recovery_decisions pentaho_recovery_decisions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_decisions
    ADD CONSTRAINT pentaho_recovery_decisions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pentaho_recovery_links pentaho_recovery_links_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_links
    ADD CONSTRAINT pentaho_recovery_links_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pentaho_recovery_links pentaho_recovery_links_proposed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pentaho_recovery_links
    ADD CONSTRAINT pentaho_recovery_links_proposed_by_fkey FOREIGN KEY (proposed_by) REFERENCES public.users(id);


--
-- Name: pipeline_associations pipeline_associations_confirmed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_associations
    ADD CONSTRAINT pipeline_associations_confirmed_by_fkey FOREIGN KEY (confirmed_by) REFERENCES public.users(id);


--
-- Name: pipeline_associations pipeline_associations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_associations
    ADD CONSTRAINT pipeline_associations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_capabilities pipeline_capabilities_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_capabilities
    ADD CONSTRAINT pipeline_capabilities_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_connections pipeline_connections_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_connections
    ADD CONSTRAINT pipeline_connections_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_evidence pipeline_evidence_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_evidence
    ADD CONSTRAINT pipeline_evidence_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_holds pipeline_holds_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_holds
    ADD CONSTRAINT pipeline_holds_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: pipeline_holds pipeline_holds_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_holds
    ADD CONSTRAINT pipeline_holds_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_holds pipeline_holds_released_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_holds
    ADD CONSTRAINT pipeline_holds_released_by_fkey FOREIGN KEY (released_by) REFERENCES public.users(id);


--
-- Name: pipeline_integrations pipeline_integrations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_integrations
    ADD CONSTRAINT pipeline_integrations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_integrations pipeline_integrations_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_integrations
    ADD CONSTRAINT pipeline_integrations_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: pipeline_jobs pipeline_jobs_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_jobs
    ADD CONSTRAINT pipeline_jobs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_methods pipeline_methods_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_methods
    ADD CONSTRAINT pipeline_methods_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_operations pipeline_operations_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_operations
    ADD CONSTRAINT pipeline_operations_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: pipeline_operations pipeline_operations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_operations
    ADD CONSTRAINT pipeline_operations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: pipeline_operations pipeline_operations_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_operations
    ADD CONSTRAINT pipeline_operations_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.users(id);


--
-- Name: pipeline_sources pipeline_sources_legacy_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_sources
    ADD CONSTRAINT pipeline_sources_legacy_collector_id_fkey FOREIGN KEY (legacy_collector_id) REFERENCES public.collectors(id);


--
-- Name: pipeline_sources pipeline_sources_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_sources
    ADD CONSTRAINT pipeline_sources_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: remote_probe_evidence remote_probe_evidence_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_evidence
    ADD CONSTRAINT remote_probe_evidence_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.remote_probe_jobs(id) ON DELETE CASCADE;


--
-- Name: remote_probe_evidence remote_probe_evidence_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_evidence
    ADD CONSTRAINT remote_probe_evidence_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: remote_probe_evidence remote_probe_evidence_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_evidence
    ADD CONSTRAINT remote_probe_evidence_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.worker_identities(id);


--
-- Name: remote_probe_jobs remote_probe_jobs_assigned_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_jobs
    ADD CONSTRAINT remote_probe_jobs_assigned_worker_id_fkey FOREIGN KEY (assigned_worker_id) REFERENCES public.worker_identities(id) ON DELETE CASCADE;


--
-- Name: remote_probe_jobs remote_probe_jobs_collector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_jobs
    ADD CONSTRAINT remote_probe_jobs_collector_id_fkey FOREIGN KEY (collector_id) REFERENCES public.collectors(id) ON DELETE CASCADE;


--
-- Name: remote_probe_jobs remote_probe_jobs_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.remote_probe_jobs
    ADD CONSTRAINT remote_probe_jobs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: resource_conditions resource_conditions_alert_state_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_conditions
    ADD CONSTRAINT resource_conditions_alert_state_id_fkey FOREIGN KEY (alert_state_id) REFERENCES public.alert_states(id);


--
-- Name: resource_conditions resource_conditions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_conditions
    ADD CONSTRAINT resource_conditions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: resource_dependencies resource_dependencies_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_dependencies
    ADD CONSTRAINT resource_dependencies_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: resource_drafts resource_drafts_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_drafts
    ADD CONSTRAINT resource_drafts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: resource_drafts resource_drafts_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_drafts
    ADD CONSTRAINT resource_drafts_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: resource_drafts resource_drafts_service_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_drafts
    ADD CONSTRAINT resource_drafts_service_provider_id_fkey FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id);


--
-- Name: resource_mapping_issues resource_mapping_issues_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_mapping_issues
    ADD CONSTRAINT resource_mapping_issues_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: resource_parameter_activations resource_parameter_activations_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_activations
    ADD CONSTRAINT resource_parameter_activations_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: resource_parameter_activations resource_parameter_activations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_activations
    ADD CONSTRAINT resource_parameter_activations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: resource_parameter_versions resource_parameter_versions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_versions
    ADD CONSTRAINT resource_parameter_versions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: resource_parameter_versions resource_parameter_versions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_parameter_versions
    ADD CONSTRAINT resource_parameter_versions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: role_permissions role_permissions_permission_key_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_key_fkey FOREIGN KEY (permission_key) REFERENCES public.permissions(key) ON DELETE RESTRICT;


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: roles roles_service_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_service_provider_id_fkey FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id) ON DELETE RESTRICT;


--
-- Name: telemetry_receipts telemetry_receipts_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_receipts
    ADD CONSTRAINT telemetry_receipts_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.managed_agents(id);


--
-- Name: telemetry_receipts telemetry_receipts_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_receipts
    ADD CONSTRAINT telemetry_receipts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: trace_spans trace_spans_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_spans
    ADD CONSTRAINT trace_spans_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.managed_agents(id);


--
-- Name: trace_spans trace_spans_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_spans
    ADD CONSTRAINT trace_spans_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: user_role_assignments user_role_assignments_service_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role_assignments
    ADD CONSTRAINT user_role_assignments_service_provider_id_fkey FOREIGN KEY (service_provider_id) REFERENCES public.service_providers(id) ON DELETE RESTRICT;


--
-- Name: vms vms_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vms
    ADD CONSTRAINT vms_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: worker_identities worker_identities_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_identities
    ADD CONSTRAINT worker_identities_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict VYZp7kxk38cBFvkBRybL6dUosIAbBo2S46aFh7epkWP609tRBHTCOYDbX1ihDrw

