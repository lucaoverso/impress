from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SchedulingResource:
    id: int
    nome: str
    tipo: str
    descricao: str = ""
    quantidade_itens: int = 1
    imagem_capa: str = ""
    ativo: bool = True

    @classmethod
    def from_dict(cls, data: dict | None):
        if data is None:
            return None

        ativo_value = data.get("ativo")
        if isinstance(ativo_value, str):
            ativo_value = ativo_value.strip()

        return cls(
            id=int(data.get("id") or 0),
            nome=str(data.get("nome") or ""),
            tipo=str(data.get("tipo") or ""),
            descricao=str(data.get("descricao") or ""),
            quantidade_itens=max(int(data.get("quantidade_itens") or 1), 1),
            imagem_capa=str(data.get("imagem_capa") or ""),
            ativo=bool(int(ativo_value)) if ativo_value not in (True, False, None) else bool(ativo_value),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SchedulingReservation:
    id: int
    recurso_id: int
    recurso_nome: str
    recurso_tipo: str
    usuario_id: int
    professor_nome: str
    data: str
    turno: str
    aula: str
    faixa_global: int
    turma: str
    tema_aula: str
    observacao: str
    status: str
    criado_em: str | None = None
    cancelado_em: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None):
        if data is None:
            return None

        return cls(
            id=int(data.get("id") or 0),
            recurso_id=int(data.get("recurso_id") or 0),
            recurso_nome=str(data.get("recurso_nome") or ""),
            recurso_tipo=str(data.get("recurso_tipo") or ""),
            usuario_id=int(data.get("usuario_id") or 0),
            professor_nome=str(data.get("professor_nome") or ""),
            data=str(data.get("data") or ""),
            turno=str(data.get("turno") or ""),
            aula=str(data.get("aula") or ""),
            faixa_global=int(data.get("faixa_global") or 0),
            turma=str(data.get("turma") or ""),
            tema_aula=str(data.get("tema_aula") or ""),
            observacao=str(data.get("observacao") or ""),
            status=str(data.get("status") or ""),
            criado_em=str(data.get("criado_em")) if data.get("criado_em") is not None else None,
            cancelado_em=str(data.get("cancelado_em")) if data.get("cancelado_em") is not None else None,
        )

    def to_dict(self) -> dict:
        return asdict(self)
