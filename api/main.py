from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import List

from domain.entities import PromptRecord
from use_cases.create_prompt import CreatePrompt
from use_cases.search_similar import SearchSimilar
from infra.sqlite_repo import SQLitePromptRepository
from infra.faiss_index import FaissVectorIndex
from infra.embedder import SentenceTransformerEmbedder
from infra.llm_simulator import LLMSimulator

app = FastAPI()

# Dependencies
def get_prompt_repo():
    return SQLitePromptRepository(db_url="sqlite:///data/prompts.db")

def get_vector_index():
    return FaissVectorIndex(index_path="data/faiss.index")

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
    prompt: str

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
    k: int = 3,
    use_case: SearchSimilar = Depends(get_search_similar_use_case),
):
    records = use_case.execute(query, k)
    return records
