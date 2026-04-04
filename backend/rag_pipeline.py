import json
import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_PATH,
    KNOWLEDGE_GRAPH_PATH,
    RAG_SIMILARITY_THRESHOLD,
    RAG_TOP_K,
)

logger = logging.getLogger("police_bot.rag")


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.

    Retrieves relevant passages from the Chroma vector store and the
    knowledge-graph JSON, then assembles a context string for the LLM.
    """

    def __init__(self) -> None:
        self._chroma_client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None
        self._knowledge_graph: dict[str, Any] = {}
        self._kg_nodes: list[dict[str, Any]] = []
        self._initialized = False

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load Chroma DB and knowledge graph. Safe to call multiple times."""
        if self._initialized:
            return

        self._load_chroma_db()
        self._load_knowledge_graph()
        self._initialized = True
        logger.info("RAG pipeline initialized successfully")

    def _load_chroma_db(self) -> None:
        chroma_path = Path(CHROMA_DB_PATH)
        if not chroma_path.exists():
            logger.warning(
                "Chroma DB path does not exist: %s — creating empty DB",
                chroma_path,
            )
            chroma_path.mkdir(parents=True, exist_ok=True)

        try:
            self._chroma_client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=Settings(anonymized_telemetry=False),
            )
            # Try to get existing collection; fall back to creating an empty one
            try:
                self._collection = self._chroma_client.get_collection(
                    name=CHROMA_COLLECTION_NAME
                )
                count = self._collection.count()
                logger.info(
                    "Loaded Chroma collection '%s' with %d documents",
                    CHROMA_COLLECTION_NAME,
                    count,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Collection '%s' not found – creating empty collection",
                    CHROMA_COLLECTION_NAME,
                )
                self._collection = self._chroma_client.get_or_create_collection(
                    name=CHROMA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
        except Exception as exc:
            logger.error("Failed to load Chroma DB: %s", exc)
            raise RuntimeError(f"Could not load Chroma DB from {chroma_path}") from exc

    def _load_knowledge_graph(self) -> None:
        kg_path = Path(KNOWLEDGE_GRAPH_PATH)
        if not kg_path.exists():
            logger.warning("Knowledge graph JSON not found at %s", kg_path)
            return

        try:
            raw = json.loads(kg_path.read_text(encoding="utf-8"))
            self._knowledge_graph = raw if isinstance(raw, dict) else {}

            # Flatten nodes/entities for keyword search
            self._kg_nodes = self._extract_nodes(self._knowledge_graph)
            logger.info(
                "Loaded knowledge graph with %d top-level keys and %d nodes",
                len(self._knowledge_graph),
                len(self._kg_nodes),
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load knowledge graph: %s", exc)

    def _extract_nodes(self, kg: dict[str, Any]) -> list[dict[str, Any]]:
        """Recursively extract searchable text nodes from the knowledge graph."""
        nodes: list[dict[str, Any]] = []

        # Support a few common graph formats
        for key in ("nodes", "entities", "items", "sections"):
            if key in kg and isinstance(kg[key], list):
                nodes.extend(kg[key])

        # If graph is a flat dict of sections, treat each value as a node
        if not nodes:
            for key, value in kg.items():
                if isinstance(value, (str, dict)):
                    nodes.append({"id": key, "content": value if isinstance(value, str) else json.dumps(value)})
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            nodes.append(item)

        return nodes

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = RAG_TOP_K) -> list[dict[str, Any]]:
        """
        Retrieve the most relevant documents for *query*.

        Returns a list of dicts with keys: ``content``, ``metadata``, ``score``.
        """
        if not self._initialized:
            self.initialize()

        results: list[dict[str, Any]] = []

        # 1. Vector search via Chroma
        chroma_results = self._chroma_retrieve(query, top_k)
        results.extend(chroma_results)

        # 2. Keyword search in knowledge graph
        kg_results = self._kg_retrieve(query, top_k)
        results.extend(kg_results)

        # Deduplicate and sort by score (descending)
        results = self._deduplicate(results)
        results.sort(key=lambda r: r.get("score", 0), reverse=True)

        return results[:top_k]

    def _chroma_retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        if self._collection is None or self._collection.count() == 0:
            return []

        try:
            raw = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            docs = raw.get("documents", [[]])[0]
            metas = raw.get("metadatas", [[]])[0]
            distances = raw.get("distances", [[]])[0]

            results: list[dict[str, Any]] = []
            for doc, meta, dist in zip(docs, metas, distances):
                # Cosine distance → similarity score
                score = 1.0 - dist
                if score >= RAG_SIMILARITY_THRESHOLD:
                    results.append(
                        {
                            "content": doc,
                            "metadata": meta or {},
                            "score": round(score, 4),
                            "source": "chroma",
                        }
                    )
            return results
        except Exception as exc:  # noqa: BLE001
            logger.error("Chroma query failed: %s", exc)
            return []

    def _kg_retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        if not self._kg_nodes:
            return []

        query_lower = query.lower()
        keywords = [w for w in query_lower.split() if len(w) > 3]

        scored: list[tuple[float, dict[str, Any]]] = []
        for node in self._kg_nodes:
            content = self._node_to_text(node)
            if not content:
                continue
            content_lower = content.lower()
            hit_count = sum(1 for kw in keywords if kw in content_lower)
            if hit_count > 0:
                score = hit_count / max(len(keywords), 1)
                scored.append((
                    score,
                    {
                        "content": content,
                        "metadata": {"source": "knowledge_graph"},
                        "score": round(score, 4),
                        "source": "knowledge_graph",
                    },
                ))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def _node_to_text(self, node: Any) -> str:
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            parts: list[str] = []
            for key in ("content", "text", "description", "summary", "label", "name"):
                val = node.get(key)
                if val and isinstance(val, str):
                    parts.append(val)
            return " ".join(parts) if parts else json.dumps(node)
        return ""

    def _deduplicate(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for r in results:
            key = r.get("content", "")[:100]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def build_context(self, retrieved_docs: list[dict[str, Any]]) -> str:
        """Convert a list of retrieved documents into a plain-text context string."""
        if not retrieved_docs:
            return ""

        parts: list[str] = []
        for i, doc in enumerate(retrieved_docs, 1):
            content = doc.get("content", "").strip()
            meta = doc.get("metadata", {})
            source = meta.get("source", doc.get("source", "KB"))
            score = doc.get("score", 0)

            header = f"[{i}] Source: {source} (relevance: {score:.2f})"
            parts.append(f"{header}\n{content}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Combined retrieve + build
    # ------------------------------------------------------------------

    def get_context_and_sources(
        self, query: str, top_k: int = RAG_TOP_K
    ) -> tuple[str, list[dict[str, Any]]]:
        """Return (context_string, retrieved_docs) for a query."""
        docs = self.retrieve(query, top_k)
        context = self.build_context(docs)
        return context, docs

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return a status dict for the /api/status endpoint."""
        chroma_count = 0
        chroma_ok = False
        if self._collection is not None:
            try:
                chroma_count = self._collection.count()
                chroma_ok = True
            except Exception:  # noqa: BLE001
                pass

        return {
            "initialized": self._initialized,
            "chroma_db": {
                "ok": chroma_ok,
                "document_count": chroma_count,
                "path": CHROMA_DB_PATH,
            },
            "knowledge_graph": {
                "ok": bool(self._knowledge_graph),
                "node_count": len(self._kg_nodes),
                "path": KNOWLEDGE_GRAPH_PATH,
            },
        }
