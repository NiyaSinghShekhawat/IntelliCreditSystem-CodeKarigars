from config import CHROMA_DIR, CHROMA_COLLECTION_NAME, TOP_K_RESULTS
from src.schemas import ParsedDocument
from typing import List, Optional
from chromadb.config import Settings
import chromadb
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


class RAGEngine:
    """
    Retrieval Augmented Generation engine using ChromaDB.
    Stores parsed document chunks and retrieves relevant
    context for the LLM to answer credit questions.
    """

    def __init__(self):
        print("Initializing ChromaDB...")
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"ChromaDB ready. Collection: {CHROMA_COLLECTION_NAME}")

    # ─── INGEST DOCUMENT ─────────────────────────────────────────────────────

    def ingest(self, parsed: ParsedDocument, company_name: str = "unknown"):
        """
        Break document into chunks and store in ChromaDB.
        Call this for every document uploaded by the user.
        """
        if not parsed.raw_text or parsed.error:
            print(f"Skipping ingestion — no text or parse error")
            return 0

        chunks = self._chunk_text(parsed.raw_text)

        if not chunks:
            print("No chunks generated")
            return 0

        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{company_name}_{parsed.document_type.value}_{i}"
            documents.append(chunk)
            metadatas.append({
                "company": company_name,
                "doc_type": parsed.document_type.value,
                "source_file": Path(parsed.source_file).name,
                "chunk_index": i
            })
            ids.append(chunk_id)

        # Add to ChromaDB (upsert = update if exists)
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"Ingested {len(chunks)} chunks from "
              f"{Path(parsed.source_file).name}")
        return len(chunks)

    # ─── INGEST MULTIPLE ─────────────────────────────────────────────────────

    def ingest_multiple(self, parsed_docs: List[ParsedDocument],
                        company_name: str = "unknown") -> int:
        """Ingest multiple documents at once"""
        total = 0
        for doc in parsed_docs:
            total += self.ingest(doc, company_name)
        return total

    # ─── RETRIEVE ────────────────────────────────────────────────────────────

    def retrieve(self, query: str,
                 company_name: Optional[str] = None,
                 k: int = TOP_K_RESULTS) -> List[str]:
        """
        Find the most relevant document chunks for a query.
        Optionally filter by company name.
        """
        if self.collection.count() == 0:
            return []

        # Build filter if company name provided
        where = None
        if company_name:
            where = {"company": company_name}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, self.collection.count()),
                where=where
            )

            chunks = results.get("documents", [[]])[0]
            return chunks

        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

    # ─── RETRIEVE WITH METADATA ───────────────────────────────────────────────

    def retrieve_with_metadata(self, query: str,
                               company_name: Optional[str] = None,
                               k: int = TOP_K_RESULTS) -> List[dict]:
        """Retrieve chunks along with their source metadata"""
        if self.collection.count() == 0:
            return []

        where = None
        if company_name:
            where = {"company": company_name}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, self.collection.count()),
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            chunks = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            return [
                {
                    "text": chunk,
                    "metadata": meta,
                    "relevance_score": round(1 - dist, 3)
                }
                for chunk, meta, dist in zip(chunks, metadatas, distances)
            ]

        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

    # ─── BUILD CONTEXT ────────────────────────────────────────────────────────

    def build_context(self, query: str,
                      company_name: Optional[str] = None) -> str:
        """
        Build a context string from retrieved chunks.
        This gets injected into the LLM prompt.
        """
        chunks = self.retrieve(query, company_name)

        if not chunks:
            return "No relevant document context found."

        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[Source {i+1}]\n{chunk}")

        return "\n\n".join(context_parts)

    # ─── CLEAR COMPANY DATA ───────────────────────────────────────────────────

    def clear_company(self, company_name: str):
        """Remove all documents for a specific company"""
        try:
            self.collection.delete(
                where={"company": company_name}
            )
            print(f"Cleared all data for: {company_name}")
        except Exception as e:
            print(f"Error clearing company data: {e}")

    def clear_all(self):
        """Clear entire ChromaDB collection — use carefully"""
        self.client.delete_collection(CHROMA_COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        print("ChromaDB cleared.")

    # ─── STATS ────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Get collection statistics"""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": CHROMA_COLLECTION_NAME,
            "storage_path": str(CHROMA_DIR)
        }

    # ─── CHUNKING ────────────────────────────────────────────────────────────

    def _chunk_text(self, text: str,
                    chunk_size: int = 500,
                    overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for better retrieval.
        Overlap ensures context isn't lost at chunk boundaries.
        """
        if not text or len(text.strip()) == 0:
            return []

        words = text.split()
        if not words:
            return []

        chunks = []
        start = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])

            if len(chunk.strip()) > 20:  # Skip tiny chunks
                chunks.append(chunk)

            if end >= len(words):
                break

            start += chunk_size - overlap

        return chunks


# ─── QUICK TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.schemas import ParsedDocument, DocumentType

    rag = RAGEngine()

    print("\n" + "="*50)
    print("TEST: RAG Engine")
    print("="*50)

    # Create a fake parsed document
    fake_doc = ParsedDocument(
        source_file="test_gst.pdf",
        document_type=DocumentType.GST_RETURN,
        raw_text="""
        GSTIN: 27AABCU9603R1ZX
        Legal Name: ABC PRIVATE LIMITED
        Total Turnover: 45,00,000
        IGST: 2,50,000 CGST: 1,25,000 SGST: 1,25,000
        ITC Claimed: 80,000
        The company has been filing GST returns regularly since 2018.
        Business involves manufacturing of auto components in Pune.
        Major clients include Tata Motors and Mahindra.
        No defaults or penalties recorded in GST portal.
        """
    )

    # Ingest
    print("\nIngesting document...")
    count = rag.ingest(fake_doc, company_name="ABC Private Limited")
    print(f"Chunks ingested: {count}")

    # Stats
    stats = rag.stats()
    print(f"Total chunks in DB: {stats['total_chunks']}")

    # Retrieve
    print("\nRetrieving context for query: 'What is the GST turnover?'")
    chunks = rag.retrieve(
        "What is the GST turnover?",
        company_name="ABC Private Limited"
    )
    print(f"Retrieved {len(chunks)} chunks")
    if chunks:
        print(f"First chunk preview: {chunks[0][:200]}...")

    # Build context
    print("\nBuilding context for LLM...")
    context = rag.build_context(
        "ITC claims and tax compliance",
        company_name="ABC Private Limited"
    )
    print(f"Context length: {len(context)} chars")
    print(f"Context preview: {context[:300]}...")

    # Cleanup
    rag.clear_company("ABC Private Limited")
    print("\nTest complete. ChromaDB working correctly!")
