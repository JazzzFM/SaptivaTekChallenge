# infra/sqlite_repo.py
from __future__ import annotations

from typing import Optional

from sqlmodel import SQLModel, Field, Session, create_engine

from domain.entities import PromptRecord
from domain.ports import PromptRepository


# mypy no entiende el metaclass de SQLModel; ignoramos el call-arg de "table=True".
class PromptModel(SQLModel, table=True):  # type: ignore[call-arg]
    id: str = Field(primary_key=True, index=True)
    prompt: str
    response: str
    created_at: str


class SQLitePromptRepository(PromptRepository):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False)
        SQLModel.metadata.create_all(self.engine)

    def save(self, record: PromptRecord) -> None:
        # Evitamos model_validate (Pydantic v2) para compatibilidad con SQLModel
        model = PromptModel(
            id=record.id,
            prompt=record.prompt,
            response=record.response,
            created_at=record.created_at,
        )
        with Session(self.engine) as session:
            session.add(model)
            session.commit()

    def find_by_id(self, id: str) -> Optional[PromptRecord]:
        with Session(self.engine) as session:
            model = session.get(PromptModel, id)
            if model is None:
                return None
            return PromptRecord(
                id=model.id,
                prompt=model.prompt,
                response=model.response,
                created_at=model.created_at,
            )
