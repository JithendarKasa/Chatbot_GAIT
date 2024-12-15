import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv


# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

def initialize_chromadb():
    """Initialize ChromaDB client and collection."""
    client = chromadb.PersistentClient(path=r"backend\data\vector_store")
    openai_embedding = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-ada-002",
        dimensions=1536  # Explicitly define dimensions for embeddings
    )
    try:
        collection = client.get_collection(name="video_transcriptions")
    except Exception:
        collection = client.create_collection(
            name="video_transcriptions",
            embedding_function=openai_embedding
        )
    return collection

def test_vector_store(collection):
    """Test and display all documents stored in the vector store."""
    try:
        # Get all stored documents and their metadata
        results = collection.get(include=["documents", "metadatas"])  # Removed "ids"

        print("Documents stored in the vector store:")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"\n--- Document {i + 1} ---")
            # Use metadata to infer the ID (if filename or similar metadata is used as an ID)
            doc_id = meta.get("filename", f"Document {i + 1}")  # Default to "Document X" if no filename
            print(f"ID: {doc_id}")
            print(f"Metadata: {meta}")
            print(f"Document: {doc[:200]}...")  # Display only first 200 characters of the document
    except Exception as e:
        print(f"Error querying vector store: {e}")


if __name__ == "__main__":
    # Initialize ChromaDB and test the vector store
    try:
        collection = initialize_chromadb()
        test_vector_store(collection)
    except Exception as e:
        print(f"Error: {e}")
