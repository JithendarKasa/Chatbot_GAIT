from chromadb.utils import embedding_functions
import chromadb
import os
from dotenv import load_dotenv

load_dotenv()

class RAGService:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path="./data/vector_store")
            self.collection = self.client.get_collection(name="course_materials")
        except Exception as e:
            print(f"Error initializing RAG service: {str(e)}")
            raise e
    
    def get_context(self, query, n_results=3):
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas']
            )
            
            if results and results['documents'] and results['documents'][0]:
                return " ".join(results['documents'][0])
            return ""
            
        except Exception as e:
            print(f"Error getting context: {str(e)}")
            return ""
    
    def get_source_info(self, context):
        try:
            if not context:
                return None
                
            results = self.collection.query(
                query_texts=[context[:1000]],
                n_results=1,
                include=['metadatas']
            )
            
            if results and results['metadatas'] and results['metadatas'][0]:
                return results['metadatas'][0][0]
            return None
            
        except Exception as e:
            print(f"Error getting source info: {str(e)}")
            return None