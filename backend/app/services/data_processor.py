import os
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import openai
from dotenv import load_dotenv
from pypdf import PdfReader
import gc  # For garbage collection

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf(file_path, max_pages=None):
    """Extract text from PDF files with memory management"""
    try:
        print(f"Starting to read PDF: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        print(f"File size: {os.path.getsize(file_path)} bytes")
        
        reader = PdfReader(file_path)
        print(f"PDF loaded, pages: {len(reader.pages)}")
        
        text = ""
        pages_to_process = min(len(reader.pages), max_pages) if max_pages else len(reader.pages)
        
        for i in range(pages_to_process):
            print(f"Processing page {i+1}/{pages_to_process}")
            try:
                page = reader.pages[i]
                text += page.extract_text() + "\n"
                if (i + 1) % 5 == 0:  # Garbage collect more frequently
                    gc.collect()
            except Exception as page_error:
                print(f"Error on page {i+1}: {page_error}")
                continue
                
        return text
    except Exception as e:
        print(f"Error processing PDF {file_path}: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return None

def process_directory(directory_path):
    """Process files in batches"""
    print(f"Starting to process directory: {directory_path}")
    
    # Get list of PDF files
    pdf_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    print(f"Found {len(pdf_files)} PDF files")
    all_chunks = []
    metadata = []
    
    # Process one PDF at a time
    for file_path in pdf_files:
        file_name = os.path.basename(file_path)
        print(f"\nProcessing PDF: {file_name}")
        
        try:
            # Extract text
            print("Extracting text...")
            text = extract_text_from_pdf(file_path)
            print(f"Extracted text length: {len(text) if text else 0} characters")
            
            if text:
                # Create chunks
                print("Creating chunks...")
                chunks = chunk_text(text)
                print(f"Created {len(chunks)} chunks")
                
                # Add chunks and metadata
                for chunk in chunks:
                    all_chunks.append(chunk)
                    metadata.append({
                        "source": file_path,
                        "filename": file_name,
                        "type": "pdf",
                        "chunk_size": len(chunk)
                    })
                
                print(f"Successfully processed {file_name}")
                # Force garbage collection
                gc.collect()
                print(f"Memory cleaned up after {file_name}")
            else:
                print(f"Skipped {file_name} - No text extracted")
                
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\nTotal processing complete. Generated {len(all_chunks)} chunks")
    return all_chunks, metadata

def chunk_text(text, chunk_size=2000, overlap=200, max_chunks=1000):
    """Split text into smaller chunks with less overlap and a maximum limit"""
    print(f"Starting to chunk text of length {len(text)}")
    if not text:
        return []
        
    chunks = []
    start = 0
    text_length = len(text)
    chunk_count = 0

    while start < text_length and chunk_count < max_chunks:
        end = start + chunk_size
        if end > text_length:
            end = text_length
        
        # Try to find a natural break point (period, newline, or space)
        if end < text_length:
            for break_char in ['. ', '\n', ' ']:
                natural_break = text.rfind(break_char, start, end)
                if natural_break != -1:
                    end = natural_break + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            chunk_count += 1
            if chunk_count % 10 == 0:  # Reduced progress reporting frequency
                print(f"Created {chunk_count} chunks so far...")
        
        if chunk_count >= max_chunks:
            print(f"Reached maximum chunk limit of {max_chunks}")
            break
            
        start = end
        if start < text_length:
            # Find the start of the next sentence for better overlap
            next_sentence = text.find('. ', start - overlap, start)
            if next_sentence != -1:
                start = next_sentence + 2
        
        if len(chunks) % 50 == 0:
            gc.collect()
    
    print(f"Finished creating {len(chunks)} chunks")
    return chunks

def main():
    print("Starting the process...")
    client = chromadb.PersistentClient(path="./data/vector_store")
    print("ChromaDB client initialized")
    
    # Add debug lines for directory checking
    course_materials_path = "./data/course_materials"
    print(f"Absolute path: {os.path.abspath(course_materials_path)}")
    print(f"Directory exists: {os.path.exists(course_materials_path)}")
    print(f"Is directory: {os.path.isdir(course_materials_path)}")
    
    # List all files in directory
    print("\nFiles in directory:")
    for root, dirs, files in os.walk(course_materials_path):
        for file in files:
            print(f"Found file: {file}")
    
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai.api_key,
        model_name="text-embedding-ada-002"
    )
    print("OpenAI embedding function initialized")
    
    try:
        collection = client.get_collection(name="course_materials")
        print("Found existing collection")
    except:
        print("Creating new collection")
        collection = client.create_collection(
            name="course_materials",
            embedding_function=openai_ef,
            metadata={"description": "PTRS:6224 course materials"}
        )
    
    print(f"Processing materials from: {course_materials_path}")
    
    try:
        chunks, metadata = process_directory(course_materials_path)
        print(f"Directory processing complete. Got {len(chunks)} chunks")
        
        if not chunks:
            print("No content was processed. Please check your files and directories.")
            return
        
        # Add documents in very small batches
        batch_size = 10  # Reduced batch size significantly
        total_batches = (len(chunks) - 1) // batch_size + 1
        
        print(f"\nStarting to add {len(chunks)} chunks to ChromaDB in {total_batches} batches")
        
        for i in range(0, len(chunks), batch_size):
            try:
                print(f"\nProcessing batch {i//batch_size + 1}/{total_batches}")
                batch_chunks = chunks[i:i + batch_size]
                batch_metadata = metadata[i:i + batch_size]
                batch_ids = [f"doc_{j}" for j in range(i, i + len(batch_chunks))]
                
                collection.add(
                    documents=batch_chunks,
                    metadatas=batch_metadata,
                    ids=batch_ids
                )
                print(f"Successfully added batch {i//batch_size + 1}")
                gc.collect()
                
            except Exception as e:
                print(f"Error processing batch {i//batch_size + 1}: {e}")
                traceback.print_exc()
                continue
        
        print("\nProcessing completed successfully!")
        
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()