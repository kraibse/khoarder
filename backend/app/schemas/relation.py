from pydantic import BaseModel, field_validator

VALID_KINDS = {"backlink", "related"}


class RelationCreate(BaseModel):
    from_entry_id: str
    to_entry_id: str
    kind: str

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in VALID_KINDS:
            raise ValueError(f"kind must be one of {sorted(VALID_KINDS)}")
        return v


class RelationOut(BaseModel):
    id: str
    from_entry_id: str
    to_entry_id: str
    kind: str

    model_config = {"from_attributes": True}
