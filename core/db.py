"""
core/db.py
==========
SQLAlchemy ORM models and helper functions for MAHILA SURAKSHA MARG.

Tables
------
  trusted_contacts   – saved SOS contacts (phase 7)
  trip_shares        – live trip-sharing status (phase 7)
  community_reports  – anonymous safety/hazard reports (phase 8)

Design
------
- SQLite only (no server needed, works offline).
- Explicit columns — no magic.
- All times stored as UTC ISO-8601 strings so they survive Python version
  changes and are human-readable in a SQLite browser.
- Personal data (contacts, trip info) can be deleted via delete_my_data().

Usage
-----
    from core.db import get_engine, init_db, add_contact, get_contacts

    engine = get_engine()
    init_db(engine)
    add_contact(engine, "Mum", "+919876543210")
    for c in get_contacts(engine):
        print(c.name, c.phone)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import config as cfg

log = logging.getLogger(__name__)


def _utcnow_str() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ORM Base and Models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class TrustedContact(Base):
    """
    A person the user wants to alert in an SOS situation.

    Privacy: stored only on this device; never sent to a server.
    The user can delete all rows with delete_my_data().
    """
    __tablename__ = "trusted_contacts"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(100), nullable=False)
    phone      = Column(String(20),  nullable=False)   # E.164 format e.g. +919876543210
    created_at = Column(String(32),  nullable=False, default=_utcnow_str)
    # consent flag: user explicitly ticked "store this contact"
    consent_given = Column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<TrustedContact id={self.id} name={self.name!r}>"


class TripShare(Base):
    """
    A live trip-sharing entry.

    The share has a unique token that can be opened in a browser.
    Status: 'active' | 'arrived' | 'expired'
    """
    __tablename__ = "trip_shares"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    token       = Column(String(32), unique=True, nullable=False)
    origin      = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    status      = Column(String(20), nullable=False, default="active")
    lat         = Column(Float,  nullable=True)   # last known location
    lon         = Column(Float,  nullable=True)
    note        = Column(Text,   nullable=True)
    created_at  = Column(String(32), nullable=False, default=_utcnow_str)
    updated_at  = Column(String(32), nullable=False, default=_utcnow_str)

    def __repr__(self) -> str:
        return f"<TripShare token={self.token!r} status={self.status!r}>"


class CommunityReport(Base):
    """
    An anonymous safety or hazard report submitted by a user.

    Privacy: NO user identifier is stored.
    Reports lose weight over 90 days (see config.REPORT_DECAY_HALF_LIFE_DAYS).
    Demo reports are labeled with is_demo=True and shown with a warning.
    """
    __tablename__ = "community_reports"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    lat         = Column(Float,  nullable=False)
    lon         = Column(Float,  nullable=False)
    # Category: harassment, poor_lighting, isolated, broken_cctv,
    #           unsafe_transport, felt_safe (positive), other
    category    = Column(String(50),  nullable=False)
    description = Column(Text,        nullable=True)   # optional free text
    hour_of_day = Column(Integer,     nullable=True)   # 0-23
    is_demo     = Column(Boolean,     nullable=False, default=False)
    is_spam     = Column(Boolean,     nullable=False, default=False)
    created_at  = Column(String(32),  nullable=False, default=_utcnow_str)
    # weight decays from 1.0 to ~0 over months (updated by a cron-like call)
    weight      = Column(Float,       nullable=False, default=1.0)

    def __repr__(self) -> str:
        return f"<CommunityReport id={self.id} cat={self.category!r}>"


class RouteFeedback(Base):
    """
    User feedback for taken routes to enhance and calibrate the safety model.
    Powers continuous learning and route risk adaptation.
    """
    __tablename__ = "route_feedbacks"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    route_type         = Column(String(30),  nullable=False)  # Fastest, Safest, Balanced
    origin             = Column(String(200), nullable=False)
    destination        = Column(String(200), nullable=False)
    rating             = Column(Integer,     nullable=False, default=4)  # 1-5 stars
    felt_safe          = Column(Boolean,     nullable=False, default=True)
    lighting_rating    = Column(Integer,     nullable=False, default=3)  # 1-5
    crowd_rating       = Column(Integer,     nullable=False, default=3)  # 1-5
    police_patrol_seen = Column(Boolean,     nullable=False, default=False)
    feedback_tags      = Column(String(200), nullable=True)  # comma separated
    comments           = Column(Text,        nullable=True)
    travel_hour        = Column(Integer,     nullable=True)
    created_at         = Column(String(32),  nullable=False, default=_utcnow_str)

    def __repr__(self) -> str:
        return f"<RouteFeedback id={self.id} route={self.route_type!r} rating={self.rating}>"


# ---------------------------------------------------------------------------
# Engine & Session factory
# ---------------------------------------------------------------------------

_engine = None


def get_engine():
    """
    Return (and cache) the SQLAlchemy engine.
    Creates the SQLite file and directory if they do not exist.
    """
    global _engine
    if _engine is None:
        cfg.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{cfg.DB_PATH}"
        _engine = create_engine(url, echo=False, future=True,
                                connect_args={"check_same_thread": False})
        log.info("SQLite engine created: %s", cfg.DB_PATH)
    return _engine


def get_session() -> Session:
    """Return a new Session bound to the shared engine."""
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return factory()


def init_db(engine=None) -> None:
    """
    Create all tables if they do not already exist.
    Safe to call repeatedly — it will not drop existing data.

    Call this once at startup (from scripts/04_init_db.py or the app).
    """
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    log.info("Database tables created / verified: %s", cfg.DB_PATH)


# ---------------------------------------------------------------------------
# Trusted contacts CRUD
# ---------------------------------------------------------------------------

def add_contact(engine, name: str, phone: str, consent: bool = True) -> TrustedContact:
    """
    Insert a new TrustedContact row.

    Parameters
    ----------
    name    : Display name (e.g. "Mum").
    phone   : Phone number in any format; prefer E.164 (+919876543210).
    consent : Must be True — contacts are only stored with explicit consent.
    """
    if not consent:
        raise ValueError("Cannot store contact without user consent.")
    with Session(engine) as session:
        contact = TrustedContact(
            name=name,
            phone=phone,
            consent_given=True,
            created_at=_utcnow_str(),
        )
        session.add(contact)
        session.commit()
        session.refresh(contact)
        log.info("Contact saved: %s", contact)
        return contact


def get_contacts(engine) -> list[TrustedContact]:
    """Return all saved TrustedContact rows."""
    with Session(engine) as session:
        return session.query(TrustedContact).all()


def delete_contact(engine, contact_id: int) -> bool:
    """Delete one contact by id. Returns True if deleted, False if not found."""
    with Session(engine) as session:
        contact = session.get(TrustedContact, contact_id)
        if contact is None:
            return False
        session.delete(contact)
        session.commit()
        return True


# ---------------------------------------------------------------------------
# Trip sharing CRUD
# ---------------------------------------------------------------------------

def create_trip_share(
    engine,
    origin: str,
    destination: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    note: Optional[str] = None,
) -> TripShare:
    """Create a new TripShare with a random token."""
    import secrets
    token = secrets.token_hex(16)
    with Session(engine) as session:
        trip = TripShare(
            token=token,
            origin=origin,
            destination=destination,
            lat=lat,
            lon=lon,
            note=note,
            status="active",
            created_at=_utcnow_str(),
            updated_at=_utcnow_str(),
        )
        session.add(trip)
        session.commit()
        session.refresh(trip)
        return trip


def get_trip_share(engine, token: str) -> Optional[TripShare]:
    """Return a TripShare by token, or None."""
    with Session(engine) as session:
        return session.query(TripShare).filter_by(token=token).first()


def update_trip_status(
    engine,
    token: str,
    status: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> bool:
    """Update status and optionally location for a TripShare."""
    with Session(engine) as session:
        trip = session.query(TripShare).filter_by(token=token).first()
        if trip is None:
            return False
        trip.status     = status
        trip.updated_at = _utcnow_str()
        if lat is not None:
            trip.lat = lat
        if lon is not None:
            trip.lon = lon
        session.commit()
        return True


# ---------------------------------------------------------------------------
# Community reports CRUD
# ---------------------------------------------------------------------------

def add_report(
    engine,
    lat: float,
    lon: float,
    category: str,
    description: Optional[str] = None,
    hour_of_day: Optional[int] = None,
    is_demo: bool = False,
    is_spam: bool = False,
) -> CommunityReport:
    """Insert an anonymous community report."""
    with Session(engine) as session:
        report = CommunityReport(
            lat=lat,
            lon=lon,
            category=category,
            description=description,
            hour_of_day=hour_of_day,
            is_demo=is_demo,
            is_spam=is_spam,
            weight=1.0,
            created_at=_utcnow_str(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return report


def get_reports(
    engine,
    exclude_spam: bool = True,
    exclude_demo: bool = False,
    limit: int = 2000,
) -> list[CommunityReport]:
    """
    Return community reports, newest first.

    Parameters
    ----------
    exclude_spam : Filter out rows marked as spam.
    exclude_demo : Filter out demo rows (useful for real mode).
    limit        : Maximum rows to return.
    """
    with Session(engine) as session:
        q = session.query(CommunityReport)
        if exclude_spam:
            q = q.filter(CommunityReport.is_spam == False)   # noqa: E712
        if exclude_demo:
            q = q.filter(CommunityReport.is_demo == False)   # noqa: E712
        q = q.order_by(CommunityReport.created_at.desc()).limit(limit)
        return q.all()


def decay_report_weights(engine) -> int:
    """
    Recalculate time-decay weights for all community reports.

    weight = 0.5 ^ (age_days / HALF_LIFE_DAYS)

    Returns the number of rows updated.
    """
    import math
    half_life = cfg.REPORT_DECAY_HALF_LIFE_DAYS
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        reports = session.query(CommunityReport).all()
        updated = 0
        for r in reports:
            try:
                created = datetime.fromisoformat(r.created_at)
                age_days = (now - created).total_seconds() / 86400
                r.weight = math.pow(0.5, age_days / half_life)
                updated += 1
            except Exception:
                pass
        session.commit()
    return updated


# ---------------------------------------------------------------------------
# Route Feedback CRUD (Model Enhancement & Calibration)
# ---------------------------------------------------------------------------

def add_route_feedback(
    engine,
    route_type: str,
    origin: str,
    destination: str,
    rating: int = 4,
    felt_safe: bool = True,
    lighting_rating: int = 3,
    crowd_rating: int = 3,
    police_patrol_seen: bool = False,
    feedback_tags: Optional[str] = None,
    comments: Optional[str] = None,
    travel_hour: Optional[int] = None,
) -> RouteFeedback:
    """Save user rating and experience feedback for a route."""
    with Session(engine) as session:
        feedback = RouteFeedback(
            route_type=route_type,
            origin=origin,
            destination=destination,
            rating=rating,
            felt_safe=felt_safe,
            lighting_rating=lighting_rating,
            crowd_rating=crowd_rating,
            police_patrol_seen=police_patrol_seen,
            feedback_tags=feedback_tags,
            comments=comments,
            travel_hour=travel_hour,
            created_at=_utcnow_str(),
        )
        session.add(feedback)
        session.commit()
        session.refresh(feedback)
        log.info("Saved route feedback id=%d for %s", feedback.id, route_type)
        return feedback


def get_route_feedbacks(engine, limit: int = 500) -> list[RouteFeedback]:
    """Retrieve recent route feedbacks."""
    with Session(engine) as session:
        return (
            session.query(RouteFeedback)
            .order_by(RouteFeedback.created_at.desc())
            .limit(limit)
            .all()
        )


def get_feedback_summary(engine) -> dict:
    """Generate statistical summary of user feedback to tune model and routing."""
    with Session(engine) as session:
        feedbacks = session.query(RouteFeedback).all()
        if not feedbacks:
            return {
                "total_count": 0,
                "avg_rating": 4.0,
                "safe_percentage": 100.0,
                "avg_lighting": 3.5,
                "avg_crowd": 3.0,
                "police_sighting_rate": 20.0,
            }
        total = len(feedbacks)
        avg_rating = sum(f.rating for f in feedbacks) / total
        safe_pct = (sum(1 for f in feedbacks if f.felt_safe) / total) * 100
        avg_lighting = sum(f.lighting_rating for f in feedbacks) / total
        avg_crowd = sum(f.crowd_rating for f in feedbacks) / total
        police_pct = (sum(1 for f in feedbacks if f.police_patrol_seen) / total) * 100

        return {
            "total_count": total,
            "avg_rating": round(avg_rating, 2),
            "safe_percentage": round(safe_pct, 1),
            "avg_lighting": round(avg_lighting, 2),
            "avg_crowd": round(avg_crowd, 2),
            "police_sighting_rate": round(police_pct, 1),
        }


# ---------------------------------------------------------------------------
# "Delete my data" — removes all personal data rows
# ---------------------------------------------------------------------------

def delete_my_data(engine) -> dict[str, int]:
    """
    Remove all personally-identifying rows:
    - All TrustedContact rows
    - All TripShare rows

    CommunityReport rows are anonymous and are NOT deleted here.
    Returns a dict with counts of deleted rows.
    """
    deleted = {}
    with Session(engine) as session:
        n_contacts = session.query(TrustedContact).count()
        session.query(TrustedContact).delete()

        n_trips = session.query(TripShare).count()
        session.query(TripShare).delete()

        session.commit()
        deleted["contacts"] = n_contacts
        deleted["trip_shares"] = n_trips

    log.info("delete_my_data: removed %s", deleted)
    return deleted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = get_engine()
    init_db(engine)
    print(f"✅ Database ready at {cfg.DB_PATH}")

    # Quick smoke test
    c = add_contact(engine, "Test Contact", "+919000000000")
    print(f"   Added: {c}")
    print(f"   All contacts: {get_contacts(engine)}")
    delete_contact(engine, c.id)
    print(f"   After delete: {get_contacts(engine)}")
