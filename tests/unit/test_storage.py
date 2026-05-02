import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_hall.storage.audit_repository import AuditRepository


def test_audit_repository_file_roundtrip(tmp_path):
    repo = AuditRepository(path=tmp_path / "audit.jsonl", database_url=None)
    repo.save_event({"run_id": "r1", "overall_reliability": 88, "risk_level": "MEDIUM"})
    repo.save_event({"run_id": "r2", "overall_reliability": 92, "risk_level": "LOW"})

    recent = repo.recent_events(limit=10)
    assert recent[0]["run_id"] == "r2"
    assert recent[1]["run_id"] == "r1"

    summary = repo.analytics_summary()
    assert summary["total_runs"] == 2
    assert summary["average_reliability"] == 90
    assert summary["risk_distribution"]["LOW"] == 1
