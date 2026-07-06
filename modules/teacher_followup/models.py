from enum import StrEnum


class FollowupRecordType(StrEnum):
    POSITIVE = "positive"
    ATTENTION = "attention"
    GUIDANCE = "guidance"
    INFORMATIVE = "informative"


class FollowupMode(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    HYBRID = "hybrid"


class FollowupTargetRole(StrEnum):
    TEACHER = "teacher"
    COORDINATOR = "coordinator"
    ADMINISTRATIVE = "administrative"
    SUPPORT = "support"


RECORD_TYPE_LABELS = {
    FollowupRecordType.POSITIVE.value: "Positivo",
    FollowupRecordType.ATTENTION.value: "Ponto de atenção",
    FollowupRecordType.GUIDANCE.value: "Orientação",
    FollowupRecordType.INFORMATIVE.value: "Informativo",
}

MODE_LABELS = {
    FollowupMode.AUTOMATIC.value: "Automático",
    FollowupMode.MANUAL.value: "Manual",
    FollowupMode.HYBRID.value: "Híbrido",
}

TARGET_ROLE_LABELS = {
    FollowupTargetRole.TEACHER.value: "Professor",
    FollowupTargetRole.COORDINATOR.value: "Coordenador",
    FollowupTargetRole.ADMINISTRATIVE.value: "Administrativo",
    FollowupTargetRole.SUPPORT.value: "Apoio",
}
