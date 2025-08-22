from sqlmodel import Field, Session, SQLModel, create_engine
from domain.entities import PromptRecord
from domain.ports import PromptRepository

class PromptModel(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    prompt: str
    response: str
    created_at: str

class SQLitePromptRepository(PromptRepository):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        SQLModel.metadata.create_all(self.engine)

    def save(self, record: PromptRecord):
        with Session(self.engine) as session:
            model = PromptModel.from_orm(record)
            session.add(model)
            session.commit()

    def find_by_id(self, id: str) -> PromptRecord | None:
        with Session(self.engine) as session:
            model = session.get(PromptModel, id)
            if model:
                return PromptRecord(**model.dict())
            return None
