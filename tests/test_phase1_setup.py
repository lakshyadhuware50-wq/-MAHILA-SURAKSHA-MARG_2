"""
tests/test_phase1_setup.py
==========================
Smoke tests for the project skeleton. Run with:

    pytest -q

These tests must pass before you move on to Phase 2.
"""

from pathlib import Path

import config as cfg


def test_folders_are_created():
    for folder in (cfg.DATA_DIR, cfg.RAW_DIR, cfg.PROCESSED_DIR, cfg.MODEL_DIR):
        assert folder.is_dir(), f"{folder} should exist"


def test_pilot_bbox_is_sane():
    north, south, east, west = cfg.PILOT_BBOX
    assert north > south, "north must be greater than south"
    assert east > west, "east must be greater than west"
    # Roughly Delhi, not accidentally London or New York.
    assert 28.0 < south < north < 29.0
    assert 76.5 < west < east < 78.0


def test_pilot_centre_inside_bbox():
    lat, lon = cfg.pilot_center()
    north, south, east, west = cfg.PILOT_BBOX
    assert south <= lat <= north
    assert west <= lon <= east


def test_disclaimer_is_present():
    assert "Safer does not mean safe" in cfg.DISCLAIMER
    assert "112" in cfg.DISCLAIMER


def test_twilio_check_does_not_crash_without_keys():
    # With no .env values this must simply return False.
    assert isinstance(cfg.twilio_is_configured(), bool)


def test_db_path_is_absolute():
    assert Path(cfg.DB_PATH).is_absolute()
