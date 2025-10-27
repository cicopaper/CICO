from typing import List, Dict, Any, Union
from openai import OpenAI
import numpy as np
import faiss 
import json
from tqdm import tqdm                  

EMBED_MODEL='Qwen3/Qwen3-Embedding-8B'
EMBED_URL='http://0.0.0.0:3456/v1'

def embedding(text: Union[str, List[str]]) -> List[float]:
    client = OpenAI(base_url=EMBED_URL, api_key='token-abc')
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return [r.embedding for r in response.data]


class Vector_Faiss:
    """
    Vector index using faiss
    """
    def __init__(self, d=1536):
        self.d = d
        self.batch_size = 1
        self.index = faiss.IndexFlatL2(d)  # build the index
        self.docs = []   # index to doc element: {'key': str, 'value': str, 'meta': dict}

    def add_docs(self, docs: List[dict]):
        self.docs.extend(docs)  # add docs to the list
        embeddings = []
        with tqdm(total=len(docs), desc="Computing embeddings") as pbar:
            for i in range(0, len(docs), self.batch_size):
                batch_docs = docs[i:i + self.batch_size]
                batch_embeds = embedding([i['key'] for i in batch_docs])  # compute embeddings
                embeddings.extend(batch_embeds)
                pbar.update(len(batch_docs))
        embeddings = np.array(embeddings)
        self.index.add(embeddings)  # add embeddings to the index
    
    def search_query(self, query, top_k, return_scores=False):
        q_embed = embedding(query)
        q_embed = np.array(q_embed)
        D, I = self.index.search(q_embed, top_k)  # search
        related_docs = [self.docs[i] for i,d in zip(I[0], D[0])]  # get the docs
        if return_scores:
            related_docs = [{'value':i['value'], 'score': d} for i, d in zip(related_docs, D[0])]
        return related_docs
    
    def save(self, path):
        faiss.write_index(self.index, path)
        with open(path + '.json', 'w') as f:
            json.dump(self.docs, f)
    
    @staticmethod
    def load(path):
        index = faiss.read_index(path)
        with open(path + '.json', 'r') as f:
            docs = json.load(f)
        indexer = Vector_Faiss()
        indexer.index = index
        indexer.docs = docs
        return indexer
