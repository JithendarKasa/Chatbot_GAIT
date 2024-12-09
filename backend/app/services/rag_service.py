import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv

load_dotenv()

class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./data/vector_store")
        self.collection = self.client.get_collection(
            name="course_materials",
            embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-ada-002"
            )
        )
    
    def get_context(self, query, n_results=3):
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if results and results['documents']:
                return " ".join(results['documents'][0])
            return ""
            
        except Exception as e:
            print(f"Error getting context: {str(e)}")
            return ""
    
    def get_source_info(self, context):
        # This is a simple implementation - you might want to enhance this
        try:
            results = self.collection.query(
                query_texts=[context[:1000]],  # Use first 1000 chars to match
                n_results=1
            )
            
            if results and results['metadatas']:
                return results['metadatas'][0][0]  # Return first metadata entry
            return None
            
        except Exception as e:
            print(f"Error getting source info: {str(e)}")
            return None