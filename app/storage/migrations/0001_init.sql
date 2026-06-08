-- 组织表
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS business_lines (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(tenant_id, code)
);

-- Agent 定义
CREATE TABLE IF NOT EXISTS agent_templates (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    version INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    yaml_source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT,
    UNIQUE(code, version)
);

CREATE TABLE IF NOT EXISTS agent_instances (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES agent_templates(id),
    business_line_id TEXT REFERENCES business_lines(id),
    config_override_json TEXT
);

-- 执行：Session / Run / Step
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_instance_id TEXT REFERENCES agent_instances(id),
    user_id TEXT,
    business_line_id TEXT,
    state_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_active_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    agent_instance_id TEXT REFERENCES agent_instances(id),
    business_line_id TEXT,
    input TEXT NOT NULL,
    output TEXT,
    status TEXT NOT NULL,
    error TEXT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_session ON runs(session_id);
CREATE INDEX IF NOT EXISTS idx_runs_business_line ON runs(business_line_id);

CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    seq INTEGER NOT NULL,
    parent_step_id TEXT REFERENCES steps(id),
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    business_line_id TEXT,
    model_id TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_tokens INTEGER,
    tool_name TEXT,
    tool_args_hash TEXT,
    payload_json TEXT,
    error_json TEXT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at TEXT,
    UNIQUE(run_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id);
CREATE INDEX IF NOT EXISTS idx_steps_parent ON steps(parent_step_id);

-- 能力元数据
CREATE TABLE IF NOT EXISTS tools (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    version TEXT NOT NULL,
    schema_json TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(code, version)
);

-- 审计事件（Phase 2 启用，Phase 0 表先建）
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES runs(id),
    step_id TEXT REFERENCES steps(id),
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_events(run_id);
