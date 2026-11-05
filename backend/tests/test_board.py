import pytest
import asyncio
from app.realtime.board import Board, BoardItem


def create_sample_item(id=1, version=1, stage="drafting"):
    return BoardItem(
        id=id,
        trip_id=1,
        venue_id="v_3391",
        venue_name="Taberna da Rua",
        category="dinner",
        day_index=1,
        start_time="12:00",
        end_time="13:30",
        lifecycle_stage=stage,
        pinned_by_user_id=10,
        position_version=version,
        price_per_person=22.0
    )


@pytest.mark.asyncio
async def test_lifecycle_transitions():
    board = Board(trip_id=1, items=[create_sample_item(id=1, stage="drafting")])

    # 1. drafting -> voting by planner (ok)
    status, reason, it = await board.transition(1, "voting", actor_role="planner")
    assert status == "ok"
    assert it.lifecycle_stage == "voting"
    assert it.position_version == 2

    # 2. voting -> locked by planner (ok)
    status, reason, it = await board.transition(1, "locked", actor_role="planner")
    assert status == "ok"
    assert it.lifecycle_stage == "locked"
    assert it.position_version == 3

    # 3. locked -> drafting by planner (rejected: only leader can override locked)
    status, reason, it = await board.transition(1, "drafting", actor_role="planner")
    assert status == "rejected"
    assert reason == "insufficient_role"

    # 4. locked -> drafting by leader (ok)
    status, reason, it = await board.transition(1, "drafting", actor_role="leader")
    assert status == "ok"
    assert it.lifecycle_stage == "drafting"
    assert it.position_version == 4

    # 5. drafting -> locked directly by leader (ok)
    status, reason, it = await board.transition(1, "locked", actor_role="leader")
    assert status == "ok"
    assert it.lifecycle_stage == "locked"


@pytest.mark.asyncio
async def test_stale_position_version_conflict():
    item = create_sample_item(id=1, version=2)
    board = Board(trip_id=1, items=[item])

    status, reason, it = await board.move(
        item_id=1,
        seen_version=1,
        day=2,
        start_time="14:00",
        end_time="15:30",
        actor_role="planner"
    )
    assert status == "conflict"
    assert reason == "version_mismatch"
    assert it.position_version == 2


@pytest.mark.asyncio
async def test_concurrent_move_one_winner_one_conflict():
    item = create_sample_item(id=1, version=1)
    board = Board(trip_id=1, items=[item])

    task1 = board.move(item_id=1, seen_version=1, day=1, start_time="14:00", end_time="15:00", actor_role="planner")
    task2 = board.move(item_id=1, seen_version=1, day=1, start_time="16:00", end_time="17:00", actor_role="planner")

    res1, res2 = await asyncio.gather(task1, task2)

    statuses = [res1[0], res2[0]]
    assert "ok" in statuses
    assert "conflict" in statuses
    assert statuses.count("ok") == 1
    assert statuses.count("conflict") == 1
    assert board.items[1].position_version == 2
