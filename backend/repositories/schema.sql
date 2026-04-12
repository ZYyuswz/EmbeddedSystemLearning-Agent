CREATE TABLE IF NOT EXISTS board_profiles (
    id TEXT PRIMARY KEY,
    vendor TEXT NOT NULL,
    model TEXT NOT NULL,
    mcu_soc TEXT NOT NULL,
    flash_kb INTEGER,
    ram_kb INTEGER,
    programmers_json TEXT NOT NULL,
    frameworks_json TEXT NOT NULL,
    pin_map_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(vendor, model)
);

CREATE TABLE IF NOT EXISTS source_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_profile_id TEXT NOT NULL,
    url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    version_tag TEXT,
    checksum TEXT,
    FOREIGN KEY(board_profile_id) REFERENCES board_profiles(id)
);

CREATE INDEX IF NOT EXISTS idx_source_refs_fetched_at ON source_refs(fetched_at);

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    board_model TEXT NOT NULL,
    knowledge_id TEXT NOT NULL,
    workspace_path TEXT NOT NULL,
    build_command TEXT NOT NULL,
    flash_command TEXT NOT NULL,
    run_check_command TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_tasks (
    task_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    command TEXT NOT NULL,
    cwd TEXT,
    logs_json TEXT NOT NULL,
    artifacts_json TEXT NOT NULL,
    error_code TEXT,
    started_at TEXT,
    ended_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_project_tasks_core ON project_tasks(project_id, task_type, status);

CREATE TABLE IF NOT EXISTS safety_policies (
    board_model TEXT PRIMARY KEY,
    requires_confirm_before_flash INTEGER NOT NULL,
    allowed_programmers_json TEXT NOT NULL,
    forbidden_commands_json TEXT NOT NULL,
    max_flash_retry INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_reports (
    report_id TEXT PRIMARY KEY,
    evaluation_task_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    board_platform TEXT NOT NULL,
    feasibility_level TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    findings_json TEXT NOT NULL,
    improvement_proposals_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_task_id ON evaluation_reports(evaluation_task_id);

CREATE TABLE IF NOT EXISTS evaluation_tasks (
    evaluation_task_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    board_platform TEXT NOT NULL,
    scenario_name TEXT NOT NULL,
    checklist_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_probe_snapshots (
    probe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    serial_ports_json TEXT NOT NULL,
    usb_devices_json TEXT NOT NULL,
    scanned_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_probe_request_id ON device_probe_snapshots(request_id);

CREATE TABLE IF NOT EXISTS board_match_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    candidate_model TEXT NOT NULL,
    score REAL NOT NULL,
    signal_breakdown_json TEXT NOT NULL,
    decision TEXT NOT NULL,
    need_confirm INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_match_request_id ON board_match_traces(request_id);

CREATE TABLE IF NOT EXISTS serial_run_check_reports (
    report_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    port TEXT NOT NULL,
    baudrate INTEGER NOT NULL,
    probe_command TEXT,
    expect_keywords_json TEXT NOT NULL,
    assert_mode TEXT NOT NULL,
    captured_lines_json TEXT NOT NULL,
    matched_keywords_json TEXT NOT NULL,
    passed INTEGER NOT NULL,
    failure_reason TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runcheck_task_id ON serial_run_check_reports(task_id);

CREATE TABLE IF NOT EXISTS knowledge_cache_entries (
    cache_key TEXT PRIMARY KEY,
    board_model TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    source_digest TEXT NOT NULL,
    ttl_sec INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_cache_board_model ON knowledge_cache_entries(board_model);

CREATE TABLE IF NOT EXISTS project_template_registry (
    template_id TEXT PRIMARY KEY,
    board_family TEXT NOT NULL,
    framework TEXT NOT NULL,
    toolchain TEXT NOT NULL,
    template_version TEXT NOT NULL,
    entry_files_json TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_template_lookup ON project_template_registry(board_family, framework, toolchain, status);

CREATE TABLE IF NOT EXISTS flash_plans (
    flash_plan_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    command TEXT NOT NULL,
    parameter_sources_json TEXT NOT NULL,
    explain TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_flash_plans_project_id ON flash_plans(project_id);
