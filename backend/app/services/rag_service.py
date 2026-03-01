import os
import time
import logging
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    """RAG service using ChromaDB for vector storage and sentence-transformers for embeddings."""

    def __init__(self, llm_service=None):
        self._chroma_client = None
        self._embedder = None
        self._collections: dict = {}
        self._llm_service = llm_service

    def _get_chroma_client(self):
        if self._chroma_client is None:
            try:
                import chromadb
                self._chroma_client = chromadb.HttpClient(host=settings.chroma_host,
                                                          port=settings.chroma_port)
                logger.info("Connected to ChromaDB at %s:%s", settings.chroma_host, settings.chroma_port)
            except Exception as e:
                logger.warning("ChromaDB unavailable: %s", e)
                return None
        return self._chroma_client

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(settings.rag_embedding_model)
                logger.info("Loaded embedding model: %s", settings.rag_embedding_model)
            except Exception as e:
                logger.warning("Embedding model unavailable: %s", e)
                return None
        return self._embedder

    def _get_or_create_collection(self, name: str):
        if name not in self._collections:
            client = self._get_chroma_client()
            if client:
                try:
                    self._collections[name] = client.get_or_create_collection(
                        name=name,
                        metadata={"hnsw:space": "cosine"}
                    )
                except Exception as e:
                    logger.warning("Failed to get/create collection %s: %s", name, e)
                    return None
        return self._collections.get(name)

    async def ingest_regulation_texts(self):
        """Ingest built-in regulation knowledge into ChromaDB."""
        collection = self._get_or_create_collection("regulations")
        if not collection:
            return {"status": "error", "message": "ChromaDB unavailable"}

        embedder = self._get_embedder()
        if not embedder:
            return {"status": "error", "message": "Embedding model unavailable"}

        # Built-in regulation snippets
        docs = self._get_regulation_snippets()
        reg_count = collection.count()
        if reg_count < len(docs):
            ids, texts, metadatas = [], [], []
            for i, doc in enumerate(docs):
                ids.append(f"reg_{i:04d}")
                texts.append(doc["text"])
                metadatas.append(doc["metadata"])
            embeddings = embedder.encode(texts).tolist()
            collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
            reg_count = len(docs)

        # Violation patterns collection
        patterns_collection = self._get_or_create_collection("violation_patterns")
        pattern_count = 0
        if patterns_collection:
            pattern_docs = self._get_violation_patterns()
            if patterns_collection.count() < len(pattern_docs):
                p_ids = [f"pat_{i:04d}" for i in range(len(pattern_docs))]
                p_texts = [d["text"] for d in pattern_docs]
                p_metas = [d["metadata"] for d in pattern_docs]
                p_embeddings = embedder.encode(p_texts).tolist()
                patterns_collection.upsert(ids=p_ids, documents=p_texts, metadatas=p_metas, embeddings=p_embeddings)
            pattern_count = patterns_collection.count()

        # Compliance rules collection (always check independently)
        compliance_count = await self._ingest_compliance_rules(embedder)

        return {"status": "ok", "message": f"Regulations: {reg_count}, patterns: {pattern_count}, compliance rules: {compliance_count}"}

    async def _ingest_compliance_rules(self, embedder) -> int:
        """Ingest compliance_rules.json into a dedicated collection for violation mapping."""
        import json as _json
        collection = self._get_or_create_collection("compliance_rules")
        if not collection:
            return 0

        rules_path = os.path.join(os.path.dirname(__file__), "..", "data", "compliance_rules.json")
        if not os.path.exists(rules_path):
            logger.warning("compliance_rules.json not found at %s", rules_path)
            return 0

        with open(rules_path, "r") as f:
            rules = _json.load(f)

        if collection.count() >= len(rules):
            return collection.count()

        ids = [f"cr_{i:04d}" for i in range(len(rules))]
        texts = [r["text"] for r in rules]
        metas = [r["metadata"] for r in rules]
        embeddings = embedder.encode(texts).tolist()
        collection.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embeddings)
        logger.info("Ingested %d compliance rules into ChromaDB", len(rules))
        return len(rules)

    async def ingest_uploaded_document(self, filename: str, content: str, doc_metadata: dict = None) -> dict:
        """Ingest a user-uploaded document into the regulations collection."""
        collection = self._get_or_create_collection("regulations")
        if not collection:
            return {"status": "error", "message": "ChromaDB unavailable"}

        embedder = self._get_embedder()
        if not embedder:
            return {"status": "error", "message": "Embedding model unavailable"}

        # Chunk the content into ~500 char segments
        chunks = self._chunk_text(content, chunk_size=500, overlap=50)
        if not chunks:
            return {"status": "error", "message": "No content to ingest"}

        base_meta = {"source": filename, "uploaded": True}
        if doc_metadata:
            base_meta.update(doc_metadata)

        base_id = f"upload_{filename.replace(' ', '_').replace('.', '_')}"
        existing = collection.count()
        ids = [f"{base_id}_{i:04d}" for i in range(len(chunks))]
        metas = [{**base_meta, "chunk": i} for i in range(len(chunks))]
        embeddings = embedder.encode(chunks).tolist()
        collection.upsert(ids=ids, documents=chunks, metadatas=metas, embeddings=embeddings)

        logger.info("Ingested uploaded document '%s': %d chunks", filename, len(chunks))
        return {"status": "ok", "message": f"Ingested {len(chunks)} chunks from '{filename}'", "chunks": len(chunks)}

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap
        return chunks

    async def similarity_search(self, query: str, collection_name: str = "regulations",
                                top_k: int = 5) -> list[dict]:
        collection = self._get_or_create_collection(collection_name)
        if not collection:
            return []

        embedder = self._get_embedder()
        if not embedder:
            return []

        query_embedding = embedder.encode([query]).tolist()
        results = collection.query(query_embeddings=query_embedding, n_results=top_k)

        chunks = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                chunks.append({
                    "content": doc,
                    "metadata": meta,
                    "relevance_score": round(1 - distance, 3),
                    "source": meta.get("regulation", "") + " " + meta.get("section", ""),
                })
        return chunks

    async def query_with_synthesis(self, query: str, regulations_filter: list[str] = None,
                                   top_k: int = 5) -> dict:
        start = time.time()
        chunks = await self.similarity_search(query, "regulations", top_k)

        synthesis = None
        if chunks:
            # Build context from retrieved chunks for LLM synthesis
            context_parts = []
            for i, c in enumerate(chunks, 1):
                source = c.get("source", "Unknown")
                content = c.get("content", "")
                context_parts.append(f"[{i}] ({source}): {content}")
            context_text = "\n\n".join(context_parts)

            # Try LLM synthesis via Ollama
            if self._llm_service and self._llm_service.llm:
                try:
                    system_prompt = (
                        "You are a regulatory compliance expert. Based on the retrieved regulation "
                        "excerpts below, provide a clear, concise synthesis answering the user's question. "
                        "Reference specific articles/sections. Be factual and precise. "
                        "Write 3-5 sentences."
                    )
                    user_msg = f"Question: {query}\n\nRelevant Regulation Excerpts:\n{context_text}"
                    synthesis = await self._llm_service.analyze_text(user_msg, system_prompt)
                except Exception as e:
                    logger.warning("LLM synthesis failed, using fallback: %s", e)

            # Fallback if LLM unavailable or failed
            if not synthesis:
                sources = [c["source"] for c in chunks]
                unique_regs = sorted(set(s.split()[0] for s in sources if s))
                synthesis = (
                    f"Based on {len(chunks)} relevant regulation excerpts from "
                    f"{', '.join(unique_regs)}, the analysis indicates compliance "
                    f"considerations apply. Please review the retrieved chunks below for details."
                )

        return {
            "query": query,
            "chunks": chunks,
            "llm_synthesis": synthesis,
            "processing_time_ms": int((time.time() - start) * 1000),
        }

    async def get_collection_stats(self) -> list[dict]:
        client = self._get_chroma_client()
        if not client:
            return []

        stats = []
        for name in ["regulations", "violation_patterns", "compliance_rules"]:
            try:
                col = client.get_or_create_collection(name)
                stats.append({
                    "collection_name": name,
                    "document_count": col.count(),
                    "embedding_dim": 384,
                })
            except Exception:
                stats.append({"collection_name": name, "document_count": 0, "embedding_dim": 384})
        return stats

    def _get_regulation_snippets(self) -> list[dict]:
        """Built-in regulation text snippets for the demo."""
        return [
            # GDPR
            {"text": "GDPR Article 4(1): 'personal data' means any information relating to an identified or identifiable natural person ('data subject'); an identifiable natural person is one who can be identified, directly or indirectly.",
             "metadata": {"regulation": "GDPR", "article": "4", "section": "1", "category": "definitions"}},
            {"text": "GDPR Article 6: Processing shall be lawful only if and to the extent that at least one of the following applies: the data subject has given consent, processing is necessary for the performance of a contract, or processing is necessary for compliance with a legal obligation.",
             "metadata": {"regulation": "GDPR", "article": "6", "section": "1", "category": "lawfulness"}},
            {"text": "GDPR Article 9: Processing of personal data revealing racial or ethnic origin, political opinions, religious or philosophical beliefs, trade union membership, genetic data, biometric data, data concerning health or data concerning a natural person's sex life or sexual orientation shall be prohibited.",
             "metadata": {"regulation": "GDPR", "article": "9", "section": "1", "category": "special_categories"}},
            {"text": "GDPR Article 17: The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay and the controller shall have the obligation to erase personal data without undue delay.",
             "metadata": {"regulation": "GDPR", "article": "17", "section": "1", "category": "data_subject_rights"}},
            {"text": "GDPR Article 22: The data subject shall have the right not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects concerning him or her or similarly significantly affects him or her.",
             "metadata": {"regulation": "GDPR", "article": "22", "section": "1", "category": "automated_decisions"}},
            {"text": "GDPR Article 32: The controller and the processor shall implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk, including encryption of personal data and ensuring confidentiality, integrity, availability and resilience of processing systems.",
             "metadata": {"regulation": "GDPR", "article": "32", "section": "1", "category": "security"}},
            {"text": "GDPR Article 44: Any transfer of personal data which are undergoing processing or are intended for processing after transfer to a third country or to an international organisation shall take place only if the conditions laid down in this Chapter are complied with.",
             "metadata": {"regulation": "GDPR", "article": "44", "section": "1", "category": "data_transfers"}},
            {"text": "GDPR Article 46: In the absence of a decision pursuant to Article 45(3), a controller or processor may transfer personal data to a third country only if the controller or processor has provided appropriate safeguards, such as Standard Contractual Clauses.",
             "metadata": {"regulation": "GDPR", "article": "46", "section": "1", "category": "data_transfers"}},
            {"text": "GDPR Recital 65: A data subject should have the right to have personal data concerning him or her rectified and a 'right to be forgotten' where the retention of such data infringes this Regulation or Union or Member State law.",
             "metadata": {"regulation": "GDPR", "recital": "65", "section": "", "category": "right_to_erasure"}},
            # HIPAA
            {"text": "HIPAA 45 CFR §164.502: A covered entity or business associate may not use or disclose protected health information, except as permitted or required. Uses and disclosures of PHI require individual authorization unless an exception applies.",
             "metadata": {"regulation": "HIPAA", "section": "164.502", "category": "uses_disclosures"}},
            {"text": "HIPAA 45 CFR §164.514: Health information that does not identify an individual and with respect to which there is no reasonable basis to believe the information can be used to identify an individual is not individually identifiable health information (de-identification standard).",
             "metadata": {"regulation": "HIPAA", "section": "164.514", "category": "de_identification"}},
            {"text": "HIPAA 45 CFR §164.530(j)(2): A covered entity must retain the documentation required for a period of 6 years from the date of its creation or the date when it last was in effect, whichever is later.",
             "metadata": {"regulation": "HIPAA", "section": "164.530(j)(2)", "category": "retention"}},
            {"text": "HIPAA 45 CFR §164.312(a)(1): A covered entity must implement technical policies and procedures for electronic information systems that maintain electronic protected health information to allow access only to those persons or software programs that have been granted access rights.",
             "metadata": {"regulation": "HIPAA", "section": "164.312(a)(1)", "category": "access_control"}},
            {"text": "HIPAA 45 CFR §164.312(e)(1): A covered entity must implement technical security measures to guard against unauthorized access to electronic protected health information that is being transmitted over an electronic communications network.",
             "metadata": {"regulation": "HIPAA", "section": "164.312(e)(1)", "category": "transmission_security"}},
            {"text": "HIPAA Business Associate Agreement: A covered entity may disclose PHI to a business associate and may allow a business associate to create, receive, maintain, or transmit PHI on its behalf, only if satisfactory assurance is obtained in the form of a BAA.",
             "metadata": {"regulation": "HIPAA", "section": "164.502(e)", "category": "business_associates"}},
            # PCI-DSS
            {"text": "PCI DSS Requirement 3.2: Do not store sensitive authentication data after authorization (even if encrypted). Sensitive authentication data includes full track data, card verification code/value (CVV/CVC), and PIN/PIN block.",
             "metadata": {"regulation": "PCI-DSS", "requirement": "3.2", "section": "", "category": "data_storage"}},
            {"text": "PCI DSS Requirement 3.4: Render PAN unreadable anywhere it is stored by using strong one-way hash functions, truncation, index tokens, or strong cryptography with associated key-management processes and procedures.",
             "metadata": {"regulation": "PCI-DSS", "requirement": "3.4", "section": "", "category": "data_masking"}},
            {"text": "PCI DSS Requirement 4.1: Use strong cryptography and security protocols to safeguard sensitive cardholder data during transmission over open, public networks, including TLS 1.2 or higher.",
             "metadata": {"regulation": "PCI-DSS", "requirement": "4.1", "section": "", "category": "encryption_transit"}},
            {"text": "PCI DSS Requirement 7.1: Limit access to system components and cardholder data to only those individuals whose job requires such access. Access must be assigned based on individual personnel's job classification and function.",
             "metadata": {"regulation": "PCI-DSS", "requirement": "7.1", "section": "", "category": "access_control"}},
            {"text": "PCI DSS Requirement 10.2: Implement automated audit trails for all system components to reconstruct events including all individual user accesses to cardholder data and all actions taken by any individual with root or administrative privileges.",
             "metadata": {"regulation": "PCI-DSS", "requirement": "10.2", "section": "", "category": "audit_trails"}},
        ]

    def _get_violation_patterns(self) -> list[dict]:
        """Known violation pattern examples for embedding similarity matching."""
        return [
            {"text": "Patient medical record sent to external AI chatbot for summarization without authorization",
             "metadata": {"category": "PHI", "severity": "CRITICAL", "regulation": "HIPAA"}},
            {"text": "Credit card number included in AI prompt for transaction analysis",
             "metadata": {"category": "PCI", "severity": "CRITICAL", "regulation": "PCI-DSS"}},
            {"text": "Employee social security number pasted into AI assistant for tax form help",
             "metadata": {"category": "PII", "severity": "HIGH", "regulation": "GDPR"}},
            {"text": "Patient diagnosis and treatment plan shared with AI for clinical decision support",
             "metadata": {"category": "PHI", "severity": "HIGH", "regulation": "HIPAA"}},
            {"text": "Full name, date of birth, and home address sent to external AI service",
             "metadata": {"category": "PII", "severity": "HIGH", "regulation": "GDPR"}},
            {"text": "API key or password included in code snippet sent to AI coding assistant",
             "metadata": {"category": "SECRET", "severity": "CRITICAL", "regulation": "INTERNAL"}},
            {"text": "Cardholder name and expiration date included in AI-generated email",
             "metadata": {"category": "PCI", "severity": "HIGH", "regulation": "PCI-DSS"}},
            {"text": "Medical lab results and imaging reports uploaded to AI for interpretation",
             "metadata": {"category": "PHI", "severity": "CRITICAL", "regulation": "HIPAA"}},
            {"text": "EU citizen personal data transferred to US-based AI service without safeguards",
             "metadata": {"category": "PII", "severity": "HIGH", "regulation": "GDPR"}},
            {"text": "CVV security code included in payment processing AI request",
             "metadata": {"category": "PCI", "severity": "CRITICAL", "regulation": "PCI-DSS"}},
        ]
