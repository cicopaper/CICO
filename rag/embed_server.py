from fastapi import FastAPI, HTTPException
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import uvicorn
import os
import argparse

app = FastAPI(title="Embeddings API")

DEFAULT_EMBED_MODEL = 'Qwen3/Qwen3-Embedding-8B'
DEFAULT_EMBED_PORT = 3456
DEFAULT_MAX_SEQ_LENGTH = 16384

EMBED_MODEL = os.environ.get("EMBED_MODEL", DEFAULT_EMBED_MODEL)
EMBED_PORT = int(os.environ.get("EMBED_PORT", DEFAULT_EMBED_PORT))
MAX_SEQ_LENGTH = int(os.environ.get("MAX_SEQ_LENGTH", DEFAULT_MAX_SEQ_LENGTH))

model = None

def get_model():
    global model
    if model is None:
        model = SentenceTransformer(EMBED_MODEL, trust_remote_code=True)
        model.max_seq_length = MAX_SEQ_LENGTH
    return model


def set_config(model_path: Optional[str] = None, port: Optional[int] = None, max_seq_length: Optional[int] = None):
    global EMBED_MODEL, EMBED_PORT, MAX_SEQ_LENGTH
    if model_path:
        EMBED_MODEL = model_path
    if port is not None:
        EMBED_PORT = int(port)
    if max_seq_length is not None:
        MAX_SEQ_LENGTH = int(max_seq_length)

@app.on_event("startup")
async def startup_event():
    get_model()
    print("Model loaded successfully!")

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: Optional[str] = None
    encoding_format: Optional[str] = "float"
    user: Optional[str] = None

class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[Dict[str, Any]]
    model: str

@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    input_texts = request.input if isinstance(request.input, list) else [request.input]
    
    try:
        embeddings = model.encode(input_texts)
        
        data = []
        for i, embedding in enumerate(embeddings):
            item = {
                "object": "embedding",
                "embedding": embedding.tolist(),
                "index": i
            }
            data.append(item)
        
        return EmbeddingResponse(
            data=data,
            model=request.model or EMBED_MODEL,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run embeddings FastAPI server with configurable model and port.")
    parser.add_argument("--model-path", "-m", dest="model_path", default=None,
                        help="Path to embedding model")
    parser.add_argument("--port", "-p", dest="port", type=int, default=None,
                        help="Port to run the server on")
    parser.add_argument("--host", dest="host", default="0.0.0.0",
                        help="Host to bind the server to")
    parser.add_argument("--max-seq-length", dest="max_seq_length", type=int, default=None,
                        help="Maximum sequence length for the embedding model")

    args = parser.parse_args()
    # 更新运行时配置
    set_config(args.model_path, args.port, args.max_seq_length)

    print(f"Starting Embeddings API with model={EMBED_MODEL}, port={EMBED_PORT}, max_seq_length={MAX_SEQ_LENGTH}")
    uvicorn.run("embed_server:app", host=args.host, port=EMBED_PORT)
