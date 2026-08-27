"""Single ministry corridor. No side quests in this machine."""

from enum import StrEnum


class TicketStatus(StrEnum):
    RECEIVED = "received"
    HEARD = "heard"
    BRIEFED = "briefed"
    SENT_BACK = "sent_back"
    MERGED = "merged"
    PUBLISHED = "published"


ALLOWED = {
    TicketStatus.RECEIVED: {TicketStatus.HEARD, TicketStatus.SENT_BACK},
    TicketStatus.HEARD: {TicketStatus.BRIEFED, TicketStatus.MERGED, TicketStatus.SENT_BACK},
    TicketStatus.BRIEFED: {TicketStatus.PUBLISHED, TicketStatus.MERGED, TicketStatus.SENT_BACK},
    TicketStatus.SENT_BACK: {TicketStatus.HEARD},
    TicketStatus.MERGED: set(),
    TicketStatus.PUBLISHED: set(),
}


def can_transition(current: TicketStatus, nxt: TicketStatus) -> bool:
    return nxt in ALLOWED[current]
