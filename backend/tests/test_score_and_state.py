from app.core.state import TicketStatus, can_transition
from app.domain.score import priority_score


def test_priority_score_adp_and_gap():
    high = priority_score(
        ticket_count=8,
        unique_voices=6,
        indicator_value=41,
        direction="higher_better",
        is_aspirational=True,
        already_funded_hint=0.05,
    )
    low = priority_score(
        ticket_count=2,
        unique_voices=2,
        indicator_value=91,
        direction="higher_better",
        is_aspirational=False,
        already_funded_hint=0.4,
    )
    assert high["score"] > low["score"]
    assert high["features"]["gap_known"] is True


def test_cannot_publish_from_received():
    assert not can_transition(TicketStatus.RECEIVED, TicketStatus.PUBLISHED)
    assert can_transition(TicketStatus.BRIEFED, TicketStatus.PUBLISHED)
