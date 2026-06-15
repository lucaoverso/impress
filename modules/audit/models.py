from enum import StrEnum


class AuditCategory(StrEnum):
    AUTH = "auth"
    PASSWORD = "password"
    PRINTING = "printing"
    SCHEDULING = "scheduling"
    ATTACHMENTS = "attachments"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
