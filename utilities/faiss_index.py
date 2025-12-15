
# Simple FAISS wrapper with disk persistence.
import os
import pickle
from typing import List, Dict, Any

try:
    import faiss
    _HAS_FAISS = True
except Exception:
    faiss = None
    _HAS_FAISS = False

class FaissIndex:
    """
    Minimal FAISS wrapper. Stores vectors in a flat index and maps metadata ids -> faiss ids.
    metadata_ids is a list parallel to embeddings when adding in batch.
    """
    def __init__(self, dim: int, index_path: str = "faiss_index.index", meta_path: str = "faiss_meta.pkl"):
        self.dim = dim
        self.index_path = index_path
        self.meta_path = meta_path
        self.meta: Dict[int, int] = {}  # faiss_id -> metadata_id
        self.next_id = 0
        self.index = None
        if _HAS_FAISS:
            self.index = faiss.IndexFlatL2(dim)
            # if files exist, try to load
            if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
                try:
                    self.index = faiss.read_index(self.index_path)
                    with open(self.meta_path, "rb") as f:
                        d = pickle.load(f)
                        self.meta = d.get("meta", {})
                        self.next_id = d.get("next_id", 0)
                except Exception:
                    # corrupted/old files -> start fresh
                    self.meta = {}
                    self.next_id = 0
        else:
            raise RuntimeError("faiss is not installed. Install faiss-cpu (or faiss) to use vector search.")

    def add(self, embeddings: List[List[float]], metadata_ids: List[int]):
        """
        Add embeddings (list of vectors) and associate each with metadata_id (e.g., DB chunk id).
        """
        if not _HAS_FAISS:
            raise RuntimeError("faiss not available")

        import numpy as np
        arr = np.array(embeddings).astype("float32")
        n = arr.shape[0]
        # append by using IndexFlatL2 + copy
        self.index.add(arr)
        # map new faiss ids to metadata ids
        for i in range(n):
            fid = self.next_id
            self.meta[fid] = metadata_ids[i]
            self.next_id += 1

    def search(self, query_vector: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Return list of {"metadata_id": <id>, "score": <distance>}
        """
        if not _HAS_FAISS:
            raise RuntimeError("faiss not available")

        import numpy as np
        q = np.array([query_vector]).astype("float32")
        distances, indices = self.index.search(q, k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            metadata_id = self.meta.get(int(idx))
            results.append({"metadata_id": metadata_id, "score": float(dist)})
        return results

    def save(self):
        """
        Persist index and metadata to disk
        """
        if not _HAS_FAISS:
            raise RuntimeError("faiss not available")
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump({"meta": self.meta, "next_id": self.next_id}, f)
