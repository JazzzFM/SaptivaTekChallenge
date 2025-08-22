from core.config import settings
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel, Field
from typing import List


from use_cases.create_prompt import CreatePrompt
from use_cases.search_similar import SearchSimilar
from infra.sqlite_repo import SQLitePromptRepository
from infra.faiss_index import FaissVectorIndex
from infra.chroma_index import ChromaVectorIndex
from infra.embedder import SentenceTransformerEmbedder
from infra.llm_simulator import LLMSimulator

app = FastAPI()

# Dependencies
def get_prompt_repo():
    return SQLitePromptRepository(db_url=settings.db_url)

def get_vector_index():
    backend = settings.vector_backend.lower()
    if backend == "chroma":
        return ChromaVectorIndex(path=settings.chroma_path)
    return FaissVectorIndex(index_path=settings.faiss_index_path)

def get_embedder():
    return SentenceTransformerEmbedder()

def get_llm_provider():
    return LLMSimulator()

def get_create_prompt_use_case(
    repo=Depends(get_prompt_repo),
    index=Depends(get_vector_index),
    embedder=Depends(get_embedder),
    llm=Depends(get_llm_provider),
):
    return CreatePrompt(llm, repo, index, embedder)

def get_search_similar_use_case(
    repo=Depends(get_prompt_repo),
    index=Depends(get_vector_index),
    embedder=Depends(get_embedder),
):
    return SearchSimilar(index, embedder, repo)


class CreatePromptRequest(BaseModel):
    prompt: str = Field(min_length=1)

class PromptResponse(BaseModel):
    id: str
    prompt: str
    response: str
    created_at: str

@app.post("/prompt", response_model=PromptResponse)
def create_prompt(
    request: CreatePromptRequest,
    use_case: CreatePrompt = Depends(get_create_prompt_use_case),
):
    record = use_case.execute(request.prompt)
    return record

@app.get("/similar", response_model=List[PromptResponse])
def search_similar(
    query: str,
    k: int = Query(3, gt=0),
    use_case: SearchSimilar = Depends(get_search_similar_use_case),
):
    records = use_case.execute(query, k)
    return records
