-- APV3 v0.2 Schema Migration
-- Run once against an existing phase20_7 database to add v0.2 tables.
-- All statements use IF NOT EXISTS / IF NOT EXISTS so re-running is safe.

-- ── 1. 8通道NT情感快照表 ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phase20_7_emotion_snapshot (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tick        INTEGER NOT NULL,
    turn_id     TEXT,
    da          REAL NOT NULL DEFAULT 0.0,
    adr         REAL NOT NULL DEFAULT 0.0,
    oxy         REAL NOT NULL DEFAULT 0.0,
    ser         REAL NOT NULL DEFAULT 0.0,
    end_val     REAL NOT NULL DEFAULT 0.0,
    cor         REAL NOT NULL DEFAULT 0.0,
    nov         REAL NOT NULL DEFAULT 0.0,
    foc         REAL NOT NULL DEFAULT 0.0,
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_emotion_snap_tick ON phase20_7_emotion_snapshot(tick DESC);
CREATE INDEX IF NOT EXISTS idx_emotion_snap_turn ON phase20_7_emotion_snapshot(turn_id);

-- ── 2. 行动器注册表 ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phase20_7_actuator_registry (
    actuator_id      TEXT PRIMARY KEY,
    conflict_group   TEXT NOT NULL DEFAULT 'default',
    action_type      TEXT NOT NULL,
    invocation_spec  TEXT NOT NULL DEFAULT 'builtin',
    param_schema     TEXT NOT NULL DEFAULT '{}',
    result_sa_type   TEXT,
    description      TEXT,
    is_seed          INTEGER NOT NULL DEFAULT 0,
    created_at       INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- ── 3. 范式注册表 ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phase20_7_paradigm_registry (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    paradigm_key      TEXT NOT NULL UNIQUE,
    state_set         TEXT NOT NULL DEFAULT '[]',
    anchor_set        TEXT NOT NULL DEFAULT '[]',
    content_src_set   TEXT NOT NULL DEFAULT '[]',
    trigger_condition TEXT,
    is_seed           INTEGER NOT NULL DEFAULT 0,
    created_at        INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- 迁移：将现有 digit_pair_colproc 范式写入注册表（is_seed=1）
INSERT OR IGNORE INTO phase20_7_paradigm_registry
    (paradigm_key, state_set, anchor_set, content_src_set, trigger_condition, is_seed)
VALUES (
    'digit_pair_colproc',
    '["digit_run_1","digit_run_2","separator"]',
    '["start_margin","advance_right","newline_align","skip_row_rightmost","step_left"]',
    '["observed_run1_next","observed_separator","observed_run2_next","recalled_column_fact","carry_digit"]',
    '{"pattern":"two_equal_digit_runs_single_sep","min_run_len":2}',
    1
);

-- ── 4. L2 group-level共现记录表 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phase20_7_l2_cooccurrence_group (
    group_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    tick        INTEGER NOT NULL,
    turn_id     TEXT,
    sa_ids      TEXT NOT NULL,
    modalities  TEXT NOT NULL DEFAULT '[]',
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_l2_group_tick ON phase20_7_l2_cooccurrence_group(tick);
CREATE INDEX IF NOT EXISTS idx_l2_group_turn ON phase20_7_l2_cooccurrence_group(turn_id);
