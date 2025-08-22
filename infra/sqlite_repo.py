# infra/sqlite_repo.py
from __future__ import annotations

from typing import Optional, Tuple, List

from sqlmodel import SQLModel, Field, Session, create_engine, select, func

from domain.entities import PromptRecord
from domain.ports import PromptRepository


class PromptModel(SQLModel, table=True):
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
    
    def find_paginated(self, offset: int = 0, limit: int = 10) -> Tuple[List[PromptRecord], int]:
        """Find records with pagination."""
        with Session(self.engine) as session:
            # Get total count
            total_stmt = select(func.count(PromptModel.id))  # type: ignore
            total = session.exec(total_stmt).one()
            
            # Get paginated records
            stmt = (
                select(PromptModel)
                .order_by(PromptModel.created_at.desc())  # type: ignore
                .offset(offset)
                .limit(limit)
            )
            models = session.exec(stmt).all()
            
            # Convert to domain objects
            records = [
                PromptRecord(
                    id=model.id,
                    prompt=model.prompt,
                    response=model.response,
                    created_at=model.created_at,
                )
                for model in models
            ]
            
            return records, total
    
    def find_all(self) -> List[PromptRecord]:
        """Find all records (use with caution in production)."""
        with Session(self.engine) as session:
            stmt = select(PromptModel).order_by(PromptModel.created_at.desc())  # type: ignore
            models = session.exec(stmt).all()
            
            return [
                PromptRecord(
                    id=model.id,
                    prompt=model.prompt,
                    response=model.response,
                    created_at=model.created_at,
                )
                for model in models
            ]
    
    def count(self) -> int:
        """Get total count of records."""
        with Session(self.engine) as session:
            stmt = select(func.count(PromptModel.id))  # type: ignore
            return session.exec(stmt).one()
