"""
tests/test_phase2.py
====================
Smoke tests for Phase 2 (data layer).

Run from the project root:
    pytest tests/test_phase2.py -v

What is tested:
  - config.py imports cleanly and has the expected values
  - geo_utils: geocode returns float coords for pilot places (offline: returns None gracefully)
  - geo_utils: distance_m gives a sane answer
  - graph_loader: loads from cache if the file exists, else returns None cleanly
  - osm_features: nearest_feature_distance handles empty GeoDataFrame gracefully
  - db: init_db creates all three tables; CRUD operations work; delete_my_data works

Nothing here touches the network. The geocoding test is skipped if
Nominatim is unreachable (CI-friendly).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_imports(self):
        import config as cfg
        assert cfg.APP_TITLE == "MAHILA SURAKSHA MARG"

    def test_pilot_bbox_valid(self):
        import config as cfg
        north, south, east, west = cfg.PILOT_BBOX
        assert north > south
        assert east  > west
        assert 28.0 < north < 30.0
        assert 77.0 < east  < 78.0

    def test_pilot_places_in_bbox(self):
        import config as cfg
        north, south, east, west = cfg.PILOT_BBOX
        for name, (lat, lon) in cfg.PILOT_PLACES.items():
            assert south <= lat <= north, f"{name} lat {lat} outside bbox"
            assert west  <= lon <= east,  f"{name} lon {lon} outside bbox"

    def test_pilot_center(self):
        import config as cfg
        lat, lon = cfg.pilot_center()
        assert 28.5 < lat < 28.7
        assert 77.1 < lon < 77.3

    def test_weights_sum_to_one(self):
        import config as cfg
        total = sum([
            cfg.WEIGHT_INCIDENT_DENSITY,
            cfg.WEIGHT_LIGHTING,
            cfg.WEIGHT_POLICE_PROXIMITY,
            cfg.WEIGHT_TRANSIT_PROXIMITY,
            cfg.WEIGHT_HOSPITAL_PROX,
            cfg.WEIGHT_ROAD_TYPE,
            cfg.WEIGHT_TIME_OF_DAY,
        ])
        assert abs(total - 1.0) < 1e-6, f"Weights sum to {total}, expected 1.0"

    def test_hour_risk_weights_length(self):
        import config as cfg
        assert len(cfg.HOUR_RISK_WEIGHTS) == 24

    def test_incident_types_probabilities_sum(self):
        import config as cfg
        total = sum(cfg.INCIDENT_TYPES.values())
        assert abs(total - 1.0) < 1e-6, f"INCIDENT_TYPES probs sum to {total}"


# ---------------------------------------------------------------------------
# Geo utils
# ---------------------------------------------------------------------------

class TestGeoUtils:
    def test_distance_m_connaught_to_lajpat(self):
        from core.geo_utils import distance_m
        import config as cfg
        cp    = cfg.PILOT_PLACES["Connaught Place"]
        lajpat = cfg.PILOT_PLACES["Lajpat Nagar"]
        d = distance_m(cp, lajpat)
        # ~8-12 km straight-line
        assert 6_000 < d < 15_000, f"Unexpected distance: {d:.0f} m"

    def test_distance_m_zero(self):
        from core.geo_utils import distance_m
        d = distance_m((28.63, 77.22), (28.63, 77.22))
        assert d < 1.0

    def test_geocode_pilot_place_offline(self):
        """
        geocode_or_pilot_place should return hard-coded coords even if
        Nominatim is unreachable, because it checks the pilot-places dict first.
        """
        from core.geo_utils import geocode_or_pilot_place
        import config as cfg
        result = geocode_or_pilot_place("Connaught Place")
        assert result is not None
        lat, lon = result
        assert 28.5 < lat < 28.7
        assert 77.1 < lon < 77.3


# ---------------------------------------------------------------------------
# Graph loader (offline — does not download)
# ---------------------------------------------------------------------------

class TestGraphLoader:
    def test_get_graph_returns_none_when_no_file(self, tmp_path, monkeypatch):
        """
        When GRAPH_PATH does not exist and we cannot download, get_graph
        should return None without crashing.
        """
        import config as cfg
        monkeypatch.setattr(cfg, "GRAPH_PATH", tmp_path / "nonexistent.graphml")

        # Monkey-patch the downloader to simulate network failure
        from core import graph_loader
        original = graph_loader._download_and_cache

        def fake_download():
            return None

        monkeypatch.setattr(graph_loader, "_download_and_cache", fake_download)
        result = graph_loader.get_graph()
        assert result is None


# ---------------------------------------------------------------------------
# OSM features (offline)
# ---------------------------------------------------------------------------

class TestOSMFeatures:
    def test_nearest_feature_distance_empty(self):
        """An empty GeoDataFrame should return 9999 (safe fallback)."""
        import geopandas as gpd
        from core.osm_features import nearest_feature_distance
        empty = gpd.GeoDataFrame()
        d = nearest_feature_distance(28.63, 77.22, empty)
        assert d == 9999.0

    def test_nearest_feature_distance_known_point(self):
        """Single police station at known coords should return near-zero distance."""
        import geopandas as gpd
        from shapely.geometry import Point
        from core.osm_features import nearest_feature_distance

        spots = gpd.GeoDataFrame(
            [{"category": "police", "name": "Test", "lat": 28.63, "lon": 77.22,
              "geometry": Point(77.22, 28.63)}],
            crs="EPSG:4326",
        )
        d = nearest_feature_distance(28.63, 77.22, spots, category="police")
        assert d < 10.0  # essentially zero


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class TestDatabase:
    @pytest.fixture(autouse=True)
    def tmp_db(self, tmp_path, monkeypatch):
        """Each test gets a fresh in-memory/tmp SQLite database."""
        import config as cfg
        monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "test.db")
        # Reset the cached engine so it uses the new path
        import core.db as db
        db._engine = None
        yield

    def test_init_creates_tables(self):
        from core.db import get_engine, init_db
        from sqlalchemy import inspect
        engine = get_engine()
        init_db(engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "trusted_contacts"  in tables
        assert "trip_shares"       in tables
        assert "community_reports" in tables
        assert "route_feedbacks"   in tables

    def test_add_and_get_contact(self):
        from core.db import get_engine, init_db, add_contact, get_contacts
        engine = get_engine()
        init_db(engine)
        c = add_contact(engine, "Mum", "+919876543210")
        assert c.id is not None
        contacts = get_contacts(engine)
        assert len(contacts) == 1
        assert contacts[0].name == "Mum"

    def test_delete_contact(self):
        from core.db import get_engine, init_db, add_contact, get_contacts, delete_contact
        engine = get_engine()
        init_db(engine)
        c = add_contact(engine, "Mum", "+919876543210")
        assert delete_contact(engine, c.id) is True
        assert len(get_contacts(engine)) == 0
        assert delete_contact(engine, 999) is False  # nonexistent

    def test_add_contact_requires_consent(self):
        from core.db import get_engine, init_db, add_contact
        engine = get_engine()
        init_db(engine)
        with pytest.raises(ValueError):
            add_contact(engine, "Mum", "+919876543210", consent=False)

    def test_trip_share_roundtrip(self):
        from core.db import get_engine, init_db, create_trip_share, get_trip_share, update_trip_status
        engine = get_engine()
        init_db(engine)
        trip = create_trip_share(engine, "Connaught Place", "Saket")
        assert len(trip.token) == 32
        fetched = get_trip_share(engine, trip.token)
        assert fetched is not None
        assert fetched.status == "active"
        ok = update_trip_status(engine, trip.token, "arrived")
        assert ok is True
        fetched2 = get_trip_share(engine, trip.token)
        assert fetched2.status == "arrived"

    def test_community_report(self):
        from core.db import get_engine, init_db, add_report, get_reports
        engine = get_engine()
        init_db(engine)
        r = add_report(engine, lat=28.63, lon=77.22, category="poor_lighting",
                       hour_of_day=22)
        assert r.id is not None
        reports = get_reports(engine)
        assert len(reports) == 1
        assert reports[0].category == "poor_lighting"
        assert reports[0].weight == pytest.approx(1.0)

    def test_delete_my_data(self):
        from core.db import get_engine, init_db, add_contact, create_trip_share, delete_my_data, get_contacts
        engine = get_engine()
        init_db(engine)
        add_contact(engine, "Mum", "+91900")
        create_trip_share(engine, "A", "B")
        result = delete_my_data(engine)
        assert result["contacts"]   == 1
        assert result["trip_shares"] == 1
        assert len(get_contacts(engine)) == 0

    def test_report_weight_decay(self):
        import math
        from datetime import datetime, timezone, timedelta
        from core.db import get_engine, init_db, add_report, decay_report_weights, get_reports
        import config as cfg

        engine = get_engine()
        init_db(engine)
        r = add_report(engine, lat=28.63, lon=77.22, category="poor_lighting")

        # Manually set an old created_at
        from sqlalchemy.orm import Session
        from core.db import CommunityReport
        with Session(engine) as session:
            rec = session.get(CommunityReport, r.id)
            old_time = datetime.now(timezone.utc) - timedelta(days=90)
            rec.created_at = old_time.isoformat()
            session.commit()

        updated = decay_report_weights(engine)
        assert updated == 1
        reports = get_reports(engine)
        # weight after 90 days at half-life of 90 days should be ~0.5
        assert 0.45 < reports[0].weight < 0.55


# ---------------------------------------------------------------------------
# Synthetic data generator
# ---------------------------------------------------------------------------

class TestSyntheticGenerator:
    def test_generates_expected_shape(self):
        from core.synthetic import generate_synthetic_incidents
        df = generate_synthetic_incidents(n=100)
        assert len(df) == 100
        assert "lat"           in df.columns
        assert "risk_label"    in df.columns
        assert "is_synthetic"  in df.columns
        assert df["is_synthetic"].all()

    def test_all_points_in_bbox(self):
        import config as cfg
        from core.synthetic import generate_synthetic_incidents
        north, south, east, west = cfg.PILOT_BBOX
        df = generate_synthetic_incidents(n=200)
        assert (df["lat"] >= south).all()
        assert (df["lat"] <= north).all()
        assert (df["lon"] >= west).all()
        assert (df["lon"] <= east).all()

    def test_binary_labels(self):
        from core.synthetic import generate_synthetic_incidents
        df = generate_synthetic_incidents(n=500)
        assert set(df["risk_label"].unique()).issubset({0, 1})
        # Expect at least some of each
        assert df["risk_label"].sum() > 10
        assert (df["risk_label"] == 0).sum() > 10
