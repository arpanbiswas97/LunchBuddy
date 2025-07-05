import os
import yaml
import pytest
import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, AsyncMock

from ..config import settings
from ..bot import LunchBuddyBot, LUNCH_CONFIRMATION_KEY
from ..database import db_manager
from ..models import DietaryPreference, User
from .. import messages


# -----------------------------------------------------------------------------
# Helper to load users from tests/test_config.yaml
# -----------------------------------------------------------------------------
def load_test_users():
    path = os.path.join(os.path.dirname(__file__), "test_config.yaml")
    with open(path) as f:
        cfg = yaml.safe_load(f)

    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%A").lower()
    users = [
        User(
            telegram_id=u["telegram_id"],
            full_name=u["full_name"],
            email=u["email"],
            dietary_preference=DietaryPreference.VEG,
            preferred_days=[tomorrow],
        )
        for u in cfg["users"]
    ]
    print(f"[LOAD] Loaded {len(users)} test users from YAML")
    return users


# -----------------------------------------------------------------------------
# Fixture: bot + minimal CallbackContext
# -----------------------------------------------------------------------------
@pytest.fixture
def bot_and_ctx(monkeypatch, fake_users):
    print("[FIXTURE] Setting up bot and fake context")
    bot = LunchBuddyBot()

    class DummyBot:
        async def send_message(self, *args, **kwargs):
            pass

    dummy = DummyBot()
    ctx = SimpleNamespace(
        bot=dummy,
        bot_data={
            LUNCH_CONFIRMATION_KEY: {
                "positive_response": set(),
                "negative_response": set(),
                "window_open": False,
            }
        },
    )

    monkeypatch.setattr(db_manager, "get_enrolled_users", lambda: fake_users)
    print(
        f"[FIXTURE] Monkeypatched get_enrolled_users to return {len(fake_users)} users"
    )
    return bot, ctx


# -----------------------------------------------------------------------------
# Fixture: your YAML‐defined users
# -----------------------------------------------------------------------------
@pytest.fixture
def fake_users():
    users = load_test_users()
    return users


# -----------------------------------------------------------------------------
# Test: “Yes” response goes into positive_response and edits to YES text
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_lunch_response_yes(bot_and_ctx, fake_users):
    bot, ctx = bot_and_ctx
    user = fake_users[0]
    print(f"[TEST-YES] Starting YES test for user_id={user.telegram_id}")

    cq = SimpleNamespace(
        data="lunch_yes", answer=AsyncMock(), edit_message_text=AsyncMock()
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=user.telegram_id), callback_query=cq
    )

    ctx.bot_data[LUNCH_CONFIRMATION_KEY]["window_open"] = True
    print("[TEST-YES] window_open set to True")

    await bot.handle_lunch_response(update, ctx)

    cq.answer.assert_awaited_once()
    print("[TEST-YES] answer() was awaited once")

    cq.edit_message_text.assert_awaited_once_with(
        messages.LUNCH_CONFIRMATION_YES.strip()
    )
    print(f"[TEST-YES] edit_message_text() called with YES message")

    assert user.telegram_id in ctx.bot_data[LUNCH_CONFIRMATION_KEY]["positive_response"]
    print("[TEST-YES] user_id recorded in positive_response")

    print("[TEST-YES] YES response test passed.\n")


# -----------------------------------------------------------------------------
# Test: “No” response goes into negative_response and edits to NO text
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_lunch_response_no(bot_and_ctx, fake_users):
    bot, ctx = bot_and_ctx
    user = fake_users[1] if len(fake_users) > 1 else fake_users[0]
    print(f"[TEST-NO] Starting NO test for user_id={user.telegram_id}")

    cq = SimpleNamespace(
        data="lunch_no", answer=AsyncMock(), edit_message_text=AsyncMock()
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=user.telegram_id), callback_query=cq
    )

    ctx.bot_data[LUNCH_CONFIRMATION_KEY]["window_open"] = True
    print("[TEST-NO] window_open set to True")

    await bot.handle_lunch_response(update, ctx)

    cq.answer.assert_awaited_once()
    print("[TEST-NO] answer() was awaited once")

    cq.edit_message_text.assert_awaited_once_with(
        messages.LUNCH_CONFIRMATION_NO.strip()
    )
    print(f"[TEST-NO] edit_message_text() called with NO message")

    assert user.telegram_id in ctx.bot_data[LUNCH_CONFIRMATION_KEY]["negative_response"]
    print("[TEST-NO] user_id recorded in negative_response")

    print("[TEST-NO] NO response test passed.\n")


# -----------------------------------------------------------------------------
# Test: response after window closed edits to EXPIRED and records nothing
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_lunch_response_expired(bot_and_ctx, fake_users):
    bot, ctx = bot_and_ctx
    user = fake_users[0]
    print(f"[TEST-EXPIRED] Starting EXPIRED test for user_id={user.telegram_id}")

    cq = SimpleNamespace(
        data="lunch_yes",  # could be yes or no
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=user.telegram_id), callback_query=cq
    )

    ctx.bot_data[LUNCH_CONFIRMATION_KEY]["window_open"] = False
    print("[TEST-EXPIRED] window_open set to False")

    await bot.handle_lunch_response(update, ctx)

    cq.answer.assert_awaited_once()
    print("[TEST-EXPIRED] answer() was awaited once")

    cq.edit_message_text.assert_awaited_once_with(
        messages.LUNCH_CONFIRMATION_EXPIRED.strip()
    )
    print(f"[TEST-EXPIRED] edit_message_text() called with EXPIRED message")

    assert (
        user.telegram_id
        not in ctx.bot_data[LUNCH_CONFIRMATION_KEY]["positive_response"]
    )
    assert (
        user.telegram_id
        not in ctx.bot_data[LUNCH_CONFIRMATION_KEY]["negative_response"]
    )
    print("[TEST-EXPIRED] No responses recorded")

    print("[TEST-EXPIRED] EXPIRED response test passed.\n")
