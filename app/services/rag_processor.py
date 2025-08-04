import os
import json
import pickle
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

class RAGProcessor:
    """Retrieval-Augmented Generation processor for enhanced document extraction"""
    
    def __init__(self):
        self.openai_client = None
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if self.openai_api_key and self.openai_api_key.strip() and self.openai_api_key != 'your-openai-api-key':
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                print("RAG: OpenAI client initialized successfully")
            except Exception as e:
                print(f"RAG: Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            print("RAG: No valid OpenAI API key found, RAG features disabled")
        
        self.embedding_model = None
        self.vector_store = None
        self.document_metadata = {}
        self.knowledge_base_path = "data/rag_knowledge_base"
        self.embeddings_path = f"{self.knowledge_base_path}/embeddings.faiss"
        self.metadata_path = f"{self.knowledge_base_path}/metadata.json"
        
        if not FAISS_AVAILABLE:
            print("RAG: FAISS not available, RAG features disabled")
            return
        
        try:
            self._load_or_create_vector_store()
            print("RAG: Processor initialized successfully")
        except Exception as e:
            print(f"RAG: Failed to initialize processor: {e}")
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings using OpenAI API"""
        if not self.openai_client:
            raise Exception("OpenAI client not available")
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=texts
            )
            embeddings = np.array([item.embedding for item in response.data])
            return embeddings
        except Exception as e:
            print(f"RAG: Failed to get embeddings: {e}")
            raise
    
    def _load_or_create_vector_store(self):
        """Load existing vector store or create a new one"""
        os.makedirs(self.knowledge_base_path, exist_ok=True)
        
        if os.path.exists(self.embeddings_path) and os.path.exists(self.metadata_path):
            try:
                self.vector_store = faiss.read_index(self.embeddings_path)
                with open(self.metadata_path, 'r') as f:
                    self.document_metadata = json.load(f)
                print(f"RAG: Loaded existing vector store with {self.vector_store.ntotal} documents")
            except Exception as e:
                print(f"RAG: Failed to load existing vector store: {e}")
                self._create_new_vector_store()
        else:
            self._create_new_vector_store()
    
    def _create_new_vector_store(self):
        """Create a new FAISS vector store"""
        try:
            self.vector_store = faiss.IndexFlatIP(1536)  # OpenAI ada-002 embedding dimension
            self.document_metadata = {}
            print("RAG: Created new vector store")
        except Exception as e:
            print(f"RAG: Failed to create vector store: {e}")
            raise
    
    def add_document_to_knowledge_base(self, document_text: str, document_id: str, 
                                     extraction_data: Dict[str, Any] = None) -> bool:
        """Add a document to the RAG knowledge base"""
        if not self.openai_client or not self.vector_store:
            return False
        
        try:
            chunks = self._chunk_document(document_text)
            
            embeddings = self._get_embeddings(chunks)
            
            faiss.normalize_L2(embeddings)
            
            start_idx = self.vector_store.ntotal
            self.vector_store.add(embeddings)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                self.document_metadata[start_idx + i] = {
                    'document_id': document_id,
                    'chunk_id': chunk_id,
                    'text': chunk,
                    'extraction_data': extraction_data or {},
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            self._save_vector_store()
            print(f"RAG: Added document {document_id} with {len(chunks)} chunks to knowledge base")
            return True
            
        except Exception as e:
            print(f"RAG: Failed to add document to knowledge base: {e}")
            return False
    
    def _chunk_document(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split document into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) > 0:
                chunks.append(chunk)
        
        return chunks if chunks else [text]
    
    def retrieve_relevant_context(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant context from the knowledge base"""
        if not self.openai_client or not self.vector_store or self.vector_store.ntotal == 0:
            return []
        
        try:
            query_embedding = self._get_embeddings([query])
            faiss.normalize_L2(query_embedding)
            
            scores, indices = self.vector_store.search(query_embedding, min(top_k, self.vector_store.ntotal))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx in self.document_metadata:
                    result = self.document_metadata[idx].copy()
                    result['similarity_score'] = float(score)
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"RAG: Failed to retrieve relevant context: {e}")
            return []
    
    def generate_rag_response(self, query: str, document_text: str, 
                            extraction_requirements: str) -> Optional[Dict[str, Any]]:
        """Generate enhanced extraction using RAG"""
        if not self.openai_client:
            return None
        
        try:
            relevant_context = self.retrieve_relevant_context(query, top_k=3)
            
            context_parts = []
            for ctx in relevant_context:
                context_parts.append(f"Document: {ctx['document_id']}")
                context_parts.append(f"Content: {ctx['text'][:300]}...")
                if ctx.get('extraction_data'):
                    context_parts.append(f"Previous extraction: {json.dumps(ctx['extraction_data'], indent=2)}")
                context_parts.append("---")
            
            context_string = "\n".join(context_parts)
            
            system_prompt = """You are an expert document extraction AI with access to a knowledge base of previously processed documents. Use the provided context from similar documents to enhance your extraction accuracy and provide more comprehensive results.

            Instructions:
            1. Use the context from similar documents to understand patterns and improve extraction
            2. Extract the requested information with high accuracy
            3. Provide confidence scores for each extracted field
            4. Flag any ambiguous or uncertain extractions
            5. Include insights from similar documents when relevant
            
            Return results as JSON with this structure:
            {
                "extracted_fields": {
                    "field_name": {
                        "value": "extracted_value",
                        "confidence": 0.95,
                        "context_used": "brief description of how context helped",
                        "similar_patterns": ["pattern1", "pattern2"]
                    }
                },
                "overall_confidence": 0.85,
                "rag_insights": "insights from similar documents",
                "context_relevance": 0.90
            }"""
            
            user_prompt = f"""Extraction Requirements: {extraction_requirements}

            Context from Similar Documents:
            {context_string}

            Current Document to Extract From:
            {document_text[:2000]}

            Extract the requested information using both the current document and insights from similar documents:"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1500,
                timeout=30
            )
            
            result_text = response.choices[0].message.content
            
            try:
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = result_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    result['rag_used'] = True
                    result['context_documents'] = len(relevant_context)
                    return result
                else:
                    return {
                        'extracted_fields': {'content': {'value': result_text, 'confidence': 0.7}},
                        'overall_confidence': 0.7,
                        'rag_used': True,
                        'context_documents': len(relevant_context)
                    }
            except json.JSONDecodeError:
                return {
                    'extracted_fields': {'content': {'value': result_text, 'confidence': 0.6}},
                    'overall_confidence': 0.6,
                    'rag_used': True,
                    'context_documents': len(relevant_context)
                }
            
        except Exception as e:
            print(f"RAG: Failed to generate RAG response: {e}")
            return None
    
    def _save_vector_store(self):
        """Save vector store and metadata to disk"""
        try:
            faiss.write_index(self.vector_store, self.embeddings_path)
            with open(self.metadata_path, 'w') as f:
                json.dump(self.document_metadata, f, indent=2)
        except Exception as e:
            print(f"RAG: Failed to save vector store: {e}")
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        if not self.vector_store:
            return {'total_documents': 0, 'total_chunks': 0, 'status': 'disabled'}
        
        unique_docs = set()
        for metadata in self.document_metadata.values():
            unique_docs.add(metadata['document_id'])
        
        return {
            'total_documents': len(unique_docs),
            'total_chunks': self.vector_store.ntotal,
            'embedding_model': 'text-embedding-ada-002',
            'vector_store_type': 'FAISS',
            'status': 'active'
        }
