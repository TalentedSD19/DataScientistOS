import numpy as np
from langchain_openai import OpenAIEmbeddings

from backend.config import MANY_FILES_THRESHOLD, RETRIEVER_TOP_K, EMBEDDING_MODEL


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def retriever_node(state: dict) -> dict:
    """Only matters when there are a lot of input files (paper: N > 100). Below that,
    every file goes straight to the planner. Above it, pick the top-K files whose
    description is closest to the query by embedding cosine similarity."""
    files = state.get("input_files", [])

    if len(files) <= MANY_FILES_THRESHOLD:
        return {
            "relevant_files": files,
            "logs": [f"retriever: only {len(files)} file(s), using all of them"],
        }

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    descriptions = state.get("data_descriptions", {})

    query_vec = np.array(await embeddings.aembed_query(state["user_prompt"]))
    doc_vecs = await embeddings.aembed_documents([descriptions.get(f, "") for f in files])

    scored = [(_cosine(query_vec, np.array(vec)), f) for f, vec in zip(files, doc_vecs)]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    top = [name for _, name in scored[:RETRIEVER_TOP_K]]
    return {
        "relevant_files": top,
        "logs": [f"retriever: picked {len(top)} of {len(files)} files"],
    }
