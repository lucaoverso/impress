from enum import StrEnum


class NotificationPriority(StrEnum):
    NORMAL = "normal"
    URGENT = "urgent"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    DEAD = "dead"


class Audience(StrEnum):
    ALL = "all"
    TEACHERS = "teachers"
    MANAGERS = "managers"
