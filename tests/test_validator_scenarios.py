import importlib
import shutil
import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def validator_db(monkeypatch, tmp_path):
    """
    Copy the shipped Toonami.db to a temp location and point config/DatabaseManager at it.
    """
    project_root = Path(__file__).resolve().parents[1]
    source_db = project_root / "Toonami.db"
    if not source_db.exists():
        pytest.skip("Toonami.db fixture is missing")

    temp_db = tmp_path / "validator.db"
    shutil.copy(source_db, temp_db)

    # Point config/DatabaseManager at the temp file
    monkeypatch.setenv("DB_PATH", str(temp_db))
    import config

    importlib.reload(config)

    from API.utils.DatabaseManager import get_db_manager

    db_manager = get_db_manager()
    db_manager.close_all_connections()
    db_manager.db_path = config.DATABASE_PATH
    db_manager.refresh_schema()

    return temp_db


def _mutate_db(db_path, *statements):
    with sqlite3.connect(db_path) as conn:
        for statement in statements:
            conn.execute(statement)
        conn.commit()


def _table_exists(conn, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None


def _describe_db(db_path):
    info = {
        "platform": "unknown",
        "has_cutless_lineups": False,
        "has_cutless_schema": False,
        "has_traditional_schema": False,
        "is_cutless_mode": False
    }
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        if _table_exists(conn, "app_data"):
            row = conn.execute(
                "SELECT value FROM app_data WHERE key = 'platform_type'"
            ).fetchone()
            if row and row[0]:
                info["platform"] = row[0].lower()

            row = conn.execute(
                "SELECT value FROM app_data WHERE key = 'cutless_mode_used'"
            ).fetchone()
            info["cutless_flag"] = (
                bool(row and str(row[0]).lower() == "true")
            )
        else:
            info["cutless_flag"] = False

        def get_columns(table_name: str):
            if not _table_exists(conn, table_name):
                return []
            return [
                column[1]
                for column in conn.execute(f"PRAGMA table_info({table_name})")
            ]

        prep_columns = get_columns("commercial_injector_prep")
        info["commercial_injector_prep_columns"] = prep_columns
        info["has_cutless_schema"] = all(
            col in prep_columns
            for col in ("startTime", "endTime", "ORIGINAL_FILE_PATH", "duration")
        )
        info["has_traditional_schema"] = "Part Number" in prep_columns

        info["has_cutless_lineups"] = any(
            _table_exists(conn, f"lineup_v{version}_cutless")
            for version in range(10)
        )
        info["is_cutless_mode"] = (
            info["cutless_flag"]
            or info["has_cutless_lineups"]
            or info["has_cutless_schema"]
        )

    return info


@pytest.fixture()
def db_meta(validator_db):
    return _describe_db(validator_db)


def _run_step_validator(step_name: str):
    from API.validators.DatabaseValidator import DatabaseValidator

    validator = DatabaseValidator()
    result = validator.validate_specific_step(step_name)
    assert result is not None, f"{step_name} validator returned None"
    return result


def _mutate_or_assert_missing(
    db_path: Path,
    table_name: str,
    validator_name: str,
    mutate_statements,
    missing_message_tokens
):
    """Run mutation if table exists, otherwise assert validator reports missing-table error."""
    with sqlite3.connect(db_path) as conn:
        exists = _table_exists(conn, table_name)

    if not exists:
        result = _run_step_validator(validator_name)
        assert result.issues, f"{validator_name} produced no issues for missing {table_name}"
        lowered = [
            f"{issue.message} {issue.details}".lower()
            for issue in result.issues
        ]
        assert any(
            any(token in text for token in missing_message_tokens)
            for text in lowered
        ), f"{validator_name} did not mention missing table {table_name}"
        return result, False

    if mutate_statements:
        if isinstance(mutate_statements, str):
            mutate_statements = [mutate_statements]
        _mutate_db(db_path, *mutate_statements)

    result = _run_step_validator(validator_name)
    return result, True


MISSING_TABLE_CASES = [
    ("ToonamiChecker", ["Toonami_Episodes"]),
    ("ToonamiChecker", ["Toonami_Shows"]),
    ("LineupPrep", ["lineup_prep_out"]),
    ("BumpEncoder", ["codes"]),
    ("CommercialBreaker", ["commercial_injector_prep"]),
    ("CommercialInjector/BlockMaker", ["commercial_injector_final"]),
    ("CutlessFinalizer", [f"lineup_v{version}_cutless" for version in range(10)])
]


# ---------------------------------------------------------------------------
# Phase 0 – Platform setup
# ---------------------------------------------------------------------------

def test_app_data_requires_platform_url(validator_db):
    _mutate_db(
        validator_db,
        "UPDATE app_data SET value = 'eg. http://example' WHERE key = 'platform_url'"
    )
    result = _run_step_validator("Platform/Folder Setup")
    assert any("platform url not configured" in issue.message.lower()
               for issue in result.issues)

def test_platform_selection_requires_platform_type(validator_db):
    _mutate_db(
        validator_db,
        "UPDATE app_data SET value = '' WHERE key = 'platform_type'"
    )
    result = _run_step_validator("PlatformSelection")
    assert not result.is_completed
    assert result.issues


def test_plex_auth_requires_token_for_dizquetv(validator_db):
    _mutate_db(
        validator_db,
        "UPDATE app_data SET value = 'dizquetv' WHERE key = 'platform_type'",
        "DELETE FROM app_data WHERE key = 'plex_token'"
    )
    result = _run_step_validator("PlexAuth")
    assert any("plex token" in issue.message.lower() for issue in result.issues)


def test_foldermaker_requires_cut_and_filtered_dirs(validator_db, tmp_path, monkeypatch):
    working_dir = tmp_path / "validator_working"
    working_dir.mkdir()
    sanitized = str(working_dir).replace("'", "''")
    import config
    monkeypatch.setattr(config, "working_dir", str(working_dir), raising=False)
    _mutate_db(
        validator_db,
        "DROP TABLE IF EXISTS Toonami_Episodes",
        "DROP TABLE IF EXISTS toonami_episodes",
        f"UPDATE app_data SET value = '{sanitized}' WHERE key = 'working_folder'"
    )
    result = _run_step_validator("FolderMaker")
    messages = [issue.message.lower() for issue in result.issues]
    assert any("cut folder missing" in msg for msg in messages)
    assert any("toonami_filtered folder missing" in msg for msg in messages)


def test_foldermaker_succeeds_when_directories_exist(validator_db, tmp_path, monkeypatch):
    working_dir = tmp_path / "validator_working_success"
    cut_dir = working_dir / "cut"
    filtered_dir = working_dir / "toonami_filtered"
    filtered_dir.mkdir(parents=True)
    cut_dir.mkdir()
    sanitized = str(working_dir).replace("'", "''")
    import config
    monkeypatch.setattr(config, "working_dir", str(working_dir), raising=False)
    _mutate_db(
        validator_db,
        "DROP TABLE IF EXISTS Toonami_Episodes",
        "DROP TABLE IF EXISTS toonami_episodes",
        f"UPDATE app_data SET value = '{sanitized}' WHERE key = 'working_folder'"
    )
    result = _run_step_validator("FolderMaker")
    assert result.is_completed
    assert not any(issue.level.value in {"WARNING", "ERROR", "CRITICAL"}
                   for issue in result.issues)


# ---------------------------------------------------------------------------
# Phase 1 – Prepare Content (Content discovery + Bumps and uncut prep)
# ---------------------------------------------------------------------------

def test_toonami_checker_detects_missing_paths(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "Toonami_Episodes",
        "ToonamiChecker",
        """
        UPDATE Toonami_Episodes
        SET Full_File_Path = ''
        WHERE ROWID IN (SELECT ROWID FROM Toonami_Episodes LIMIT 5)
        """,
        ["toonami_episodes", "table not found"]
    )
    if not mutated:
        return
    assert any("file paths" in issue.message.lower() for issue in result.issues)


def test_lineup_prep_detects_missing_file_paths(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "lineup_prep_out",
        "LineupPrep",
        """
        UPDATE lineup_prep_out
        SET FULL_FILE_PATH = ''
        WHERE ROWID IN (SELECT ROWID FROM lineup_prep_out LIMIT 5)
        """,
        ["lineup_prep_out", "table not found"]
    )
    if not mutated:
        return
    assert any("bump(s) missing file paths" in issue.message.lower() for issue in result.issues)


def test_bump_encoder_requires_codes_table(validator_db):
    _mutate_db(validator_db, "DROP TABLE IF EXISTS codes")
    result = _run_step_validator("BumpEncoder")
    assert any("does not exist" in issue.message.lower() for issue in result.issues)


def test_bump_encoder_detects_blank_codes(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "codes",
        "BumpEncoder",
        """
        UPDATE codes
        SET Code = ''
        WHERE ROWID IN (
            SELECT ROWID
            FROM codes
            LIMIT 5
        )
        """,
        ["codes", "table not found"]
    )
    if not mutated:
        return
    assert any("missing code" in issue.message.lower() for issue in result.issues)


def test_uncut_encoder_requires_block_ids(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "uncut_encoded_data",
        "UncutEncoder",
        """
        UPDATE uncut_encoded_data
        SET BLOCK_ID = NULL
        WHERE ROWID IN (
            SELECT ROWID
            FROM uncut_encoded_data
            WHERE BLOCK_ID IS NOT NULL
              AND FULL_FILE_PATH LIKE '%S__E__%'
              AND LOWER(FULL_FILE_PATH) NOT LIKE '%next%'
              AND LOWER(FULL_FILE_PATH) NOT LIKE '%s00e%'
            LIMIT 200
        )
        """,
        ["uncut_encoded_data", "table not found"]
    )
    if not mutated:
        return
    assert any("missing block_id" in issue.message.lower() for issue in result.issues)


def test_multilineup_requires_reordered_tables(validator_db):
    statements = [
        f"DROP TABLE IF EXISTS multibumps_v{version}_data_reordered"
        for version in range(10)
    ]
    _mutate_db(validator_db, *statements)
    result = _run_step_validator("Multilineup")
    assert not result.is_completed


def test_merger_detects_missing_lineup_table(validator_db):
    statements = []
    for version in range(10):
        statements.append(f"DROP TABLE IF EXISTS lineup_v{version}")
        statements.append(f"DROP TABLE IF EXISTS lineup_v{version}_uncut")
    _mutate_db(validator_db, *statements)
    result = _run_step_validator("ShowScheduler/Merger")
    assert not result.is_completed


def test_episode_filter_detects_bump_paths(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "lineup_v8_uncut_filtered",
        "EpisodeFilter",
        """
        UPDATE lineup_v8_uncut_filtered
        SET FULL_FILE_PATH = '/app/bump/validator-test.mp4'
        WHERE ROWID = (SELECT ROWID FROM lineup_v8_uncut_filtered LIMIT 1)
        """,
        ["episodefilter not run", "lineup_v8_uncut_filtered", "table not found"]
    )
    if not mutated:
        return
    assert any("bump" in issue.message.lower() for issue in result.issues)


# ---------------------------------------------------------------------------
# Phase 2/3 – Commercial Detection + Prepare Cut Lineup
# ---------------------------------------------------------------------------

def test_commercial_breaker_requires_timestamps(validator_db, db_meta):
    if db_meta["has_cutless_schema"]:
        result, mutated = _mutate_or_assert_missing(
            validator_db,
            "commercial_injector_prep",
            "CommercialBreaker",
            """
            UPDATE commercial_injector_prep
            SET startTime = NULL,
                endTime = NULL
            """,
            ["commercial_injector_prep", "table not found"]
        )
        expected_phrase = "missing timestamps"
    elif db_meta["has_traditional_schema"]:
        result, mutated = _mutate_or_assert_missing(
            validator_db,
            "commercial_injector_prep",
            "CommercialBreaker",
            """
            UPDATE commercial_injector_prep
            SET "Part Number" = NULL
            WHERE ROWID IN (
                SELECT ROWID FROM commercial_injector_prep LIMIT 5
            )
            """,
            ["commercial_injector_prep", "table not found"]
        )
        expected_phrase = "part number"
    else:
        pytest.skip("commercial_injector_prep schema unavailable")

    if not mutated:
        return

    assert any(expected_phrase in issue.message.lower() for issue in result.issues)


def test_commercial_injector_prep_missing_table(validator_db):
    _mutate_db(validator_db, "DROP TABLE IF EXISTS commercial_injector_prep")
    result = _run_step_validator("CommercialInjectorPrep")
    assert any("table missing" in issue.message.lower() for issue in result.issues)


def test_commercial_injector_prep_handles_traditional_schema(validator_db, db_meta):
    if db_meta["has_cutless_schema"]:
        pytest.skip("Database uses cutless schema; traditional check not applicable")
    result = _run_step_validator("CommercialInjectorPrep")
    assert result.is_completed
    assert not any("cutless schema incomplete" in issue.message.lower()
                   for issue in result.issues)

def test_commercial_injector_detects_interleaving_error(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "commercial_injector_final",
        "CommercialInjector/BlockMaker",
        """
        UPDATE commercial_injector_final
        SET FULL_FILE_PATH = '',
            BLOCK_ID = BLOCK_ID
        WHERE ROWID IN (
            SELECT ROWID
            FROM commercial_injector_final
            WHERE FULL_FILE_PATH NOT LIKE '%bump%'
            LIMIT 3
        )
        """,
        ["commercial_injector_final", "table not found"]
    )
    if not mutated:
        return
    assert any("missing file path" in issue.message.lower() or
               "missing file paths" in issue.message.lower()
               for issue in result.issues)


def test_blockmaker_detects_missing_block_ids(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "commercial_injector_final",
        "BlockMaker",
        """
        UPDATE commercial_injector_final
        SET BLOCK_ID = NULL
        WHERE ROWID IN (
            SELECT ROWID
            FROM commercial_injector_final
            WHERE BLOCK_ID IS NOT NULL
            LIMIT 5
        )
        """,
        ["commercial_injector_final", "table not found"]
    )
    if not mutated:
        return
    assert any("missing block_ids" in issue.message.lower() or
               "no block_ids" in issue.message.lower() for issue in result.issues)


def test_blockmaker_handles_different_show_prefixes(validator_db):
    result = _run_step_validator("CommercialInjector/BlockMaker")
    assert not any("inconsistent block_id" in issue.message.lower()
                   for issue in result.issues)


def test_postcut_bump_filter_reports_not_run(validator_db):
    statements = ["DROP TABLE IF EXISTS lineup_prep_out_postcut"]
    for version in range(10):
        statements.append(f"DROP TABLE IF EXISTS multibumps_v{version}_data_postcut")
        statements.append(f"DROP TABLE IF EXISTS multibumps_v{version}_data_reordered_postcut")
    _mutate_db(validator_db, *statements)
    result = _run_step_validator("PostCutBumpFilter")
    assert any("not run" in issue.message.lower() for issue in result.issues)


def test_bump_calculator_skips_non_combreak(validator_db):
    _mutate_db(
        validator_db,
        "UPDATE app_data SET value = 'dizquetv' WHERE key = 'platform_type'"
    )
    from API.validators.steps.BumpCalculatorValidator import BumpCalculatorValidator

    validator = BumpCalculatorValidator()
    result = validator.validate()
    info_messages = [issue.message.lower() for issue in result.issues]
    assert any("not required" in msg for msg in info_messages)


def test_bump_calculator_requires_table_for_combreak(validator_db, db_meta):
    if not db_meta["has_cutless_lineups"]:
        pytest.skip("Cutless artifacts not present")

    _mutate_db(
        validator_db,
        "UPDATE app_data SET value = 'combreakdirect' WHERE key = 'platform_type'",
        "DROP TABLE IF EXISTS bump_durations"
    )
    from API.validators.steps.BumpCalculatorValidator import BumpCalculatorValidator

    validator = BumpCalculatorValidator()
    result = validator.validate()
    assert any("bump_durations table missing" in issue.message.lower()
               for issue in result.issues)


def test_cutless_finalizer_flags_missing_bump_durations(validator_db, db_meta):
    if not db_meta["has_cutless_lineups"]:
        pytest.skip("Cutless lineups not present in this database")

    statements = [
        "UPDATE app_data SET value = 'combreakdirect' WHERE key = 'platform_type'",
        """
        UPDATE lineup_v2_cutless
        SET duration = NULL
        WHERE startTime IS NULL AND endTime IS NULL
        """
    ]
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "lineup_v2_cutless",
        "CutlessFinalizer",
        statements,
        ["lineup_v2_cutless", "no cutless lineup tables"]
    )
    if not mutated:
        return
    assert any("missing duration" in issue.message.lower() for issue in result.issues)


def test_cutless_finalizer_skipped_in_traditional_mode(validator_db, db_meta):
    if db_meta["has_cutless_lineups"]:
        pytest.skip("Cutless tables exist in this database")
    result = _run_step_validator("CutlessFinalizer")
    assert result.is_completed


# ---------------------------------------------------------------------------
# Cross-cutting validators
# ---------------------------------------------------------------------------

def test_lineup_integrity_detects_intro_violation(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "lineup_v2",
        "LineupIntegrity",
        """
        WITH target AS (
            SELECT ROWID r
            FROM lineup_v2
            WHERE Code IS NOT NULL AND Code <> ''
            LIMIT 1
        ),
        next_row AS (
            SELECT MIN(ROWID) r
            FROM lineup_v2
            WHERE ROWID > (SELECT r FROM target)
        )
        UPDATE lineup_v2
        SET FULL_FILE_PATH = CASE
            WHEN ROWID = (SELECT r FROM target)
                THEN '/app/bump/validator-multibump.mp4'
            WHEN ROWID = (SELECT r FROM next_row)
                THEN '/app/bump/validator-followup.mp4'
            ELSE FULL_FILE_PATH
        END
        """,
        ["lineup_v2", "table not found"]
    )
    if not mutated:
        return
    assert any("intro" in issue.message.lower() or "multibump" in issue.message.lower()
               for issue in result.issues)


def test_referential_integrity_detects_orphan_episode(validator_db):
    result, mutated = _mutate_or_assert_missing(
        validator_db,
        "commercial_injector_final",
        "ReferentialIntegrity",
        """
        UPDATE commercial_injector_final
        SET FULL_FILE_PATH = '/app/anime/Validator Show - S97E97 - Test.mkv'
        WHERE ROWID = (
            SELECT ROWID
            FROM commercial_injector_final
            WHERE FULL_FILE_PATH NOT LIKE '%bump%'
            LIMIT 1
        )
        """,
        ["commercial_injector_final", "table not found"]
    )
    if not mutated:
        return
    assert any("orphan" in issue.message.lower() or "not found in source" in issue.message.lower()
               for issue in result.issues)


@pytest.mark.parametrize("validator_name,tables", MISSING_TABLE_CASES)
def test_required_tables_missing_are_detected(validator_db, validator_name, tables):
    statements = [f"DROP TABLE IF EXISTS {table}" for table in tables]
    _mutate_db(validator_db, *statements)
    result = _run_step_validator(validator_name)

    if validator_name == "CutlessFinalizer":
        # In traditional mode CutlessFinalizer treats missing tables as "not applicable"
        if result.get_status_description().lower().startswith("not completed"):
            assert result.issues
        else:
            assert result.is_completed
            assert any("cutless mode not detected" in issue.message.lower()
                       for issue in result.issues)
        return

    assert not result.is_completed
    assert result.issues
    combined = " ".join(
        f"{issue.message.lower()} {issue.details.lower()}"
        for issue in result.issues
    )
    for table in tables:
        assert table.lower() in combined or validator_name == "CommercialInjector/BlockMaker"
