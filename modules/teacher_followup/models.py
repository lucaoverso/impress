from enum import StrEnum


class FollowupRecordType(StrEnum):
    POSITIVE = "positive"
    ATTENTION = "attention"
    GUIDANCE = "guidance"
    INFORMATIVE = "informative"


RECORD_TYPE_LABELS = {
    FollowupRecordType.POSITIVE.value: "Positivo",
    FollowupRecordType.ATTENTION.value: "Ponto de atencao",
    FollowupRecordType.GUIDANCE.value: "Orientacao",
    FollowupRecordType.INFORMATIVE.value: "Informativo",
}
