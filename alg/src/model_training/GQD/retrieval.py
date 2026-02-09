import os
import requests
import json
import numpy as np
from typing import List, Dict
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI

from constants import (
    BOCHA_API_KEY,
    OPENAI_API_KEY,
    RETRIEVAL_TOP_K,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SIMILARITY_THRESHOLD
)


class WebRetriever:
    def __init__(self, bocha_api_key: str = None, openai_api_key: str = None):
        self.bocha_api_key = bocha_api_key or BOCHA_API_KEY or os.getenv("BOCHA_API_KEY")
        self.openai_api_key = openai_api_key or OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        
        if not self.bocha_api_key:
            raise ValueError("Bocha API key not found. Set BOCHA_API_KEY in constants.py or environment variable.")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in constants.py or environment variable.")
        
        self.bocha_search_url = "https://api.bochaai.com/v1/web-search"
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
    
    def bocha_search(self, query: str, count: int = RETRIEVAL_TOP_K) -> List[Dict]:
        headers = {
            "Authorization": f"Bearer {self.bocha_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = json.dumps({
            "query": query,
            "summary": True,
            "count": count
        })
        
        try:
            response = requests.post(
                self.bocha_search_url,
                headers=headers,
                data=payload,
                timeout=10
            )
            response.raise_for_status()
            search_results = response.json()
            
            results = []
            if search_results.get("code") == 200:
                data = search_results.get("data", {})
                web_pages = data.get("webPages", {}).get("value", [])
                
                for item in web_pages:
                    results.append({
                        "url": item.get("url", ""),
                        "title": item.get("name", ""),
                        "snippet": item.get("snippet", "")
                    })
            
            return results
        
        except Exception as e:
            print(f"Bocha search error: {e}")
            return []
    
    def fetch_webpage_content(self, url: str) -> str:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "lxml")
            
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""
    
    def get_embedding(self, text: str) -> np.ndarray:
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return np.array(response.data[0].embedding)
        
        except Exception as e:
            print(f"Embedding error: {e}")
            return np.zeros(1536)
    
    def get_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> np.ndarray:
        if not texts:
            return np.array([])
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.openai_client.embeddings.create(
                    input=batch,
                    model="text-embedding-ada-002"
                )
                
                batch_embeddings = [np.array(item.embedding) for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"Batch embedding error for batch {i//batch_size}: {e}")
                all_embeddings.extend([np.zeros(1536) for _ in batch])
        
        return np.array(all_embeddings)
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        if vec1.shape[0] == 0 or vec2.shape[0] == 0:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def cosine_similarity_batch(self, query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
        if query_vec.shape[0] == 0 or doc_vecs.shape[0] == 0:
            return np.zeros(doc_vecs.shape[0])
        
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return np.zeros(doc_vecs.shape[0])
        query_normalized = query_vec / query_norm
        
        doc_norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
        doc_norms[doc_norms == 0] = 1
        doc_normalized = doc_vecs / doc_norms
        
        similarities = np.dot(doc_normalized, query_normalized)
        
        return similarities
    
    def retrieve_and_chunk(self, query: str, original_query: str = None, 
                           threshold: float = SIMILARITY_THRESHOLD) -> List[str]:
        results = self.bocha_search(query)
        if not results:
            return []
        
        all_text = []
        for result in results[:5]:
            content = self.fetch_webpage_content(result["url"])
            if not content:
                content = result["snippet"]
            if content:
                all_text.append(content)
        
        if not all_text:
            return []
        
        all_chunks = []
        for text in all_text:
            all_chunks.extend(self.text_splitter.split_text(text))
        
        if not all_chunks:
            return []
        
        valid_chunks = [c for c in all_chunks if len(c.strip()) >= 20]
        if not valid_chunks:
            return []
        
        query_emb = self.get_embedding(query)
        chunk_embs = self.get_embeddings_batch(valid_chunks, batch_size=100)
        sims = self.cosine_similarity_batch(query_emb, chunk_embs)
        
        filtered = []
        for chunk, sim in zip(valid_chunks, sims):
            if sim > threshold:
                filtered.append({"text": chunk, "similarity": float(sim)})
        
        filtered.sort(key=lambda x: x["similarity"], reverse=True)
        return [c["text"] for c in filtered[:10]]


_retriever_instance = None

def get_retriever():
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = WebRetriever()
    return _retriever_instance

def retrieve_documents(subquery: str, original_query: str = None) -> List[str]:
    return get_retriever().retrieve_and_chunk(subquery, original_query)

