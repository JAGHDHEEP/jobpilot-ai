-- ============================================================================
-- JobPilot AI — PostgreSQL schema (reference DDL)
-- Authoritative source of truth is the SQLAlchemy models + Alembic migrations.
-- This file documents the full relational design with indexes & constraints.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- fuzzy text search on jobs/skills
CREATE EXTENSION IF NOT EXISTS "citext";       -- case-insensitive emails

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE user_role          AS ENUM ('user', 'admin');
CREATE TYPE application_status  AS ENUM ('saved','applied','interview','rejected','offer','accepted','withdrawn');
CREATE TYPE job_source          AS ENUM ('linkedin','naukri','indeed','foundit','wellfound','glassdoor','company','manual');
CREATE TYPE employment_type     AS ENUM ('full_time','part_time','contract','internship','temporary');
CREATE TYPE remote_type         AS ENUM ('onsite','hybrid','remote');
CREATE TYPE doc_kind            AS ENUM ('resume','cover_letter');

-- ---------------------------------------------------------------------------
-- Users & auth
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           CITEXT NOT NULL UNIQUE,
    hashed_password TEXT,                       -- NULL for pure-OAuth accounts
    full_name       TEXT NOT NULL,
    role            user_role NOT NULL DEFAULT 'user',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE oauth_accounts (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider      TEXT NOT NULL,                -- 'google' | 'github'
    provider_uid  TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_uid)
);

CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,           -- sha256 of opaque token
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_tokens_user ON refresh_tokens(user_id);

-- ---------------------------------------------------------------------------
-- Profile (1:1 with user) + child collections
-- ---------------------------------------------------------------------------
CREATE TABLE profiles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    phone       TEXT,
    location    TEXT,
    linkedin_url TEXT,
    github_url  TEXT,
    portfolio_url TEXT,
    headline    TEXT,
    summary     TEXT,
    languages   JSONB NOT NULL DEFAULT '[]',     -- [{name, proficiency}]
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE educations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    degree          TEXT NOT NULL,
    field_of_study  TEXT,
    institution     TEXT NOT NULL,
    gpa             NUMERIC(4,2),
    start_year      INT,
    graduation_year INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_educations_profile ON educations(profile_id);

CREATE TABLE experiences (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id  UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    company     TEXT NOT NULL,
    role        TEXT NOT NULL,
    location    TEXT,
    start_date  DATE,
    end_date    DATE,                           -- NULL => current
    is_current  BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    highlights  JSONB NOT NULL DEFAULT '[]',     -- bullet strings
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_experiences_profile ON experiences(profile_id);

CREATE TABLE projects (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id   UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    description  TEXT,
    technologies JSONB NOT NULL DEFAULT '[]',
    github_url   TEXT,
    live_url     TEXT,
    achievements JSONB NOT NULL DEFAULT '[]',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_projects_profile ON projects(profile_id);

CREATE TABLE skills (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id  UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'technical', -- technical|soft|tool|framework
    proficiency INT,                              -- 1..5
    years       NUMERIC(4,1),
    UNIQUE (profile_id, name)
);
CREATE INDEX ix_skills_profile ON skills(profile_id);
CREATE INDEX ix_skills_name_trgm ON skills USING gin (name gin_trgm_ops);

CREATE TABLE certifications (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id  UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    issuer      TEXT,
    issue_date  DATE,
    expiry_date DATE,
    credential_url TEXT
);
CREATE INDEX ix_certifications_profile ON certifications(profile_id);

CREATE TABLE achievements (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id  UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT,
    date        DATE
);
CREATE INDEX ix_achievements_profile ON achievements(profile_id);

-- ---------------------------------------------------------------------------
-- Documents (resumes / cover letters)
-- ---------------------------------------------------------------------------
CREATE TABLE documents (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind          doc_kind NOT NULL,
    title         TEXT NOT NULL,
    storage_key   TEXT,                          -- object-store key / path
    mime_type     TEXT,
    size_bytes    BIGINT,
    is_master     BOOLEAN NOT NULL DEFAULT FALSE,
    parsed_text   TEXT,                          -- extracted plain text
    structured    JSONB,                         -- parsed master-profile JSON
    job_id        UUID,                          -- set for tailored docs
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_documents_user ON documents(user_id);
CREATE INDEX ix_documents_user_kind ON documents(user_id, kind);

-- ---------------------------------------------------------------------------
-- Jobs
-- ---------------------------------------------------------------------------
CREATE TABLE jobs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source           job_source NOT NULL,
    source_job_id    TEXT,                       -- id at the origin
    title            TEXT NOT NULL,
    company          TEXT NOT NULL,
    location         TEXT,
    remote_type      remote_type,
    employment_type  employment_type,
    salary_min       NUMERIC(12,2),
    salary_max       NUMERIC(12,2),
    currency         TEXT,
    description      TEXT NOT NULL,
    requirements     JSONB NOT NULL DEFAULT '[]',
    keywords         JSONB NOT NULL DEFAULT '[]',
    experience_min   NUMERIC(4,1),
    experience_max   NUMERIC(4,1),
    posted_at        TIMESTAMPTZ,
    apply_url        TEXT,
    company_rating   NUMERIC(3,2),               -- 0..5 quality signal
    content_hash     TEXT NOT NULL,              -- dedupe key
    embedded         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, content_hash)
);
CREATE INDEX ix_jobs_posted_at ON jobs(posted_at DESC);
CREATE INDEX ix_jobs_title_trgm ON jobs USING gin (title gin_trgm_ops);
CREATE INDEX ix_jobs_company_trgm ON jobs USING gin (company gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- Match results (explainable scoring)
-- ---------------------------------------------------------------------------
CREATE TABLE job_matches (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id            UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    overall_score     INT NOT NULL,             -- 0..100
    skill_score       INT NOT NULL,
    project_score     INT NOT NULL,
    experience_score  INT NOT NULL,
    education_score   INT NOT NULL,
    keyword_score     INT NOT NULL,
    missing_skills    JSONB NOT NULL DEFAULT '[]',
    missing_keywords  JSONB NOT NULL DEFAULT '[]',
    rationale         TEXT,                      -- LLM explanation
    model_version     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, job_id)
);
CREATE INDEX ix_job_matches_user_score ON job_matches(user_id, overall_score DESC);

-- ---------------------------------------------------------------------------
-- Daily recommendations
-- ---------------------------------------------------------------------------
CREATE TABLE recommendations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id      UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    for_date    DATE NOT NULL,
    rank        INT NOT NULL,
    rank_score  NUMERIC(8,4) NOT NULL,           -- blended ranking score
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, job_id, for_date)
);
CREATE INDEX ix_recommendations_user_date ON recommendations(user_id, for_date, rank);

-- ---------------------------------------------------------------------------
-- Applications + status history
-- ---------------------------------------------------------------------------
CREATE TABLE applications (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id       UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status       application_status NOT NULL DEFAULT 'saved',
    resume_doc_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    cover_doc_id  UUID REFERENCES documents(id) ON DELETE SET NULL,
    notes        TEXT,
    applied_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, job_id)
);
CREATE INDEX ix_applications_user_status ON applications(user_id, status);

CREATE TABLE application_events (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    from_status    application_status,
    to_status      application_status NOT NULL,
    note           TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_application_events_app ON application_events(application_id);

-- ---------------------------------------------------------------------------
-- AI usage metering + audit + feedback learning
-- ---------------------------------------------------------------------------
CREATE TABLE ai_usage (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    provider       TEXT NOT NULL,
    model          TEXT NOT NULL,
    operation      TEXT NOT NULL,                -- match|optimize|cover|interview|review
    prompt_tokens  INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    cost_usd       NUMERIC(10,6) NOT NULL DEFAULT 0,
    cache_hit      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ai_usage_user_time ON ai_usage(user_id, created_at);

CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    target_type TEXT,
    target_id   TEXT,
    ip          INET,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_logs_actor_time ON audit_logs(actor_id, created_at);

CREATE TABLE feedback (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id      UUID REFERENCES jobs(id) ON DELETE CASCADE,
    signal      TEXT NOT NULL,                   -- relevant|not_relevant|good_match|bad_match
    weight      NUMERIC(4,2) NOT NULL DEFAULT 1.0,
    comment     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_feedback_user ON feedback(user_id);
