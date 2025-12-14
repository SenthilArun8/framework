import os
from typing import List, Optional
import chromadb # Phase 13 Fix
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from src.schema import MemoryFragment

class MemoryStore:
    def __init__(self, persist_directory="data/chroma_db"):
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            print(f"Embedding Init Failed: {e}. Fallback to Fake not implemented, ensure Key is valid.")
            raise e
        # Persistent Client
        client = chromadb.PersistentClient(path=persist_directory) # Initialize PersistentClient
        self.vector_store = Chroma(
            collection_name="character_backstory",
            embedding_function=self.embeddings,
            client=client # Use the initialized client
        )

    def add_memories(self, fragments: List[MemoryFragment]):
        """Embeds and stores memory fragments. Supports batching implicitly via Chroma."""
        documents = []
        for frag in fragments:
            # We embed the description, but store the whole object details in metadata
            doc = Document(
                page_content=frag.description,
                metadata={
                    "id": frag.id,
                    "time_period": frag.time_period,
                    "emotional_tags": ", ".join(frag.emotional_tags),
                    "importance_score": frag.importance_score
                }
            )
            documents.append(doc)
        
        if documents:
            # Chroma handles batching, but we could chunk if len(documents) > 1000
            self.vector_store.add_documents(documents)
            print(f"Stored {len(documents)} memories.")

    def retrieve_relevant(self, query: str, k: int = 3, min_importance: float = 0.0, 
                         filter_tags: List[str] = None, filter_time_period: str = None) -> List[MemoryFragment]:
        """
        Retrieves memories relevant to the query with multidimensional filtering.
        """
        
        # Build filter (Chroma $and syntax if multiple)
        filter_conditions = []
        
        if min_importance > 0:
            filter_conditions.append({"importance_score": {"$gte": min_importance}})
            
        if filter_time_period:
            filter_conditions.append({"time_period": filter_time_period})
            
        # Tag filtering is tricky in Chroma metadata strings. 
        # We'll use $contains if supported, or post-filter. 
        # Ideally, we store tags as a list, but Chroma Metadata must be str, int, float, bool.
        # Fallback: Post-filtering for tags if exact match isn't targeted.
        # However, for now let's apply the structural filters we can.
        
        where_filter = None
        if len(filter_conditions) == 1:
            where_filter = filter_conditions[0]
        elif len(filter_conditions) > 1:
            where_filter = {"$and": filter_conditions}
            
        results = self.vector_store.similarity_search(query, k=k*2 if filter_tags else k, filter=where_filter)
        memories = []
        
        for doc in results:
            tags = doc.metadata.get("emotional_tags", "").split(", ")
            
            # Post-filter for tags (naive "any match" logic)
            if filter_tags:
                if not any(t in tags for t in filter_tags):
                    continue
            
            mem = MemoryFragment(
                id=doc.metadata.get("id"),
                time_period=doc.metadata.get("time_period"),
                description=doc.page_content,
                emotional_tags=[t for t in tags if t], 
                importance_score=float(doc.metadata.get("importance_score", 0.0))
            )
            memories.append(mem)
        
        # Re-slice to k after post-filtering
        return memories[:k]

    def clear_memories(self):
        """Wipes the entire vector store collection."""
        try:
            # We can't delete the collection object easily from the wrapper, 
            # but we can get all IDs and delete them.
            # OR we can use the client to delete the collection.
            print("Wiping ChromaDB memories...")
            ids = self.vector_store.get()['ids']
            if ids:
                self.vector_store.delete(ids=ids)
                print(f"Deleted {len(ids)} memories from ChromaDB.")
            else:
                print("ChromaDB already empty.")
        except Exception as e:
            print(f"Error clearing ChromaDB: {e}")

def seed_memories(store: MemoryStore):
    """Seeds the database with initial backstory fragments if empty."""
    fragments = [
    # The Core Trauma (Technical Failure)
    MemoryFragment(
        id="mem_001", 
        time_period="Last Summer", 
        description="Crashed the department's $15,000 LiDAR drone into a tree because I was tired and misread the telemetry. The silence in the lab was deafening.", 
        emotional_tags=["Shame", "Guilt", "Financial Anxiety"], 
        importance_score=0.95
    ),
    # The Intellectual Anchor (Why he does this)
    MemoryFragment(
        id="mem_002", 
        time_period="Undergrad", 
        description="Mapped the informal transit networks in a developing nation. Realized that maps define reality for governments. If it's not on the map, it doesn't exist.", 
        emotional_tags=["Purpose", "Justice", "Discovery"], 
        importance_score=0.8
    ),
    # The Recurring Stressor
    MemoryFragment(
        id="mem_003", 
        time_period="Thesis Defense Prep", 
        description="Professor Halloway keeps asking for 'more human-centric qualitative data.' I don't know how to map feelings!", 
        emotional_tags=["Frustration", "Inadequacy", "Anger"], 
        importance_score=0.7
    )
    ]
    
    # Robust Seeding: Check existence first to report correctly, but use checks or upsert if supported.
    # Chroma's add_documents might error on duplicates.
    # We will use the store's underlying logic or just explicit check.
    
    existing = store.vector_store.get(ids=[f.id for f in fragments])
    existing_ids = set(existing["ids"])
    
    to_add = [f for f in fragments if f.id not in existing_ids]
    
    if to_add:
        # Use our wrapper which handles the embedding and metadata
        store.add_memories(to_add)
        print(f"Seeded {len(to_add)} new memories.")
    else:
        print("MemoryStore already seeded.")
