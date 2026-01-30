import json
import pytest
from pathlib import Path
from bot.position_manager import PositionManager, Position
from datetime import datetime, timezone

@pytest.fixture
def pm(tmp_path):
    # Use a temporary directory for tests
    return PositionManager(data_dir=str(tmp_path))

def test_add_remove_position(pm):
    pos = Position(
        token_id="test_token",
        entry_price=0.5,
        size=10.0,
        filled_size=10.0,
        entry_time=datetime.now(timezone.utc).isoformat(),
        tp=0.6,
        sl=0.4
    )
    pm.add_position(pos)
    assert pm.position_count() == 1
    assert pm.has_position("test_token")
    
    retrieved = pm.get_position("test_token")
    assert retrieved.entry_price == 0.5
    
    pm.remove_position("test_token")
    assert pm.position_count() == 0

def test_blacklist_logic(pm):
    token = "bad_token"
    pm.add_to_blacklist(token, "stop_loss", duration_days=1)
    assert pm.is_blacklisted(token) is True
    
    # Check non-existent
    assert pm.is_blacklisted("unknown") is False

def test_stats_recording(pm):
    pm.record_trade(
        entry_price=0.5,
        exit_price=0.6,
        size=10.0,
        fees=0.1,
        entry_time=datetime.now(timezone.utc).isoformat(),
        exit_time=datetime.now(timezone.utc).isoformat(),
        odds_range="0.50-0.60"
    )
    stats = pm.get_stats()
    assert stats["lifetime"]["total_trades"] == 1
    assert stats["lifetime"]["wins"] == 1
    # PnL: (0.6 - 0.5) * 10 - 0.1 = 1.0 - 0.1 = 0.9
    assert stats["lifetime"]["total_pnl"] == pytest.approx(0.9)
