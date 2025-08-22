import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from use_cases.create_prompt import CreatePrompt
from infra.sqlite_repo import SQLitePromptRepository
from infra.faiss_index import FaissVectorIndex
from infra.embedder import SentenceTransformerEmbedder
from infra.llm_simulator import LLMSimulator


def main():
    repo = SQLitePromptRepository(db_url="sqlite:///data/prompts.db")
    index = FaissVectorIndex(index_path="data/faiss.index")
    embedder = SentenceTransformerEmbedder()
    llm = LLMSimulator()
    create_prompt_use_case = CreatePrompt(llm, repo, index, embedder)

    prompts = [
        "Cómo optimizo un ETL con PySpark?",
        "Cuáles son las ventajas de usar Kubernetes?",
        "Explica el concepto de Inyección de Dependencias",
        "Cómo funciona el algoritmo de consenso Raft?",
        "Qué es la programación funcional?",
    ]

    for prompt in prompts:
        print(f"Creating prompt: {prompt}")
        create_prompt_use_case.execute(prompt)

    print("Seeding finished.")

if __name__ == "__main__":
    main()
