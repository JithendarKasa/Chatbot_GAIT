from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from PyPDF2 import PdfReader
import os
import numpy as np

class SearchService:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.documents = []
        self.vectors = None
        self.load_documents()
        
    def read_pdf(self, file_path):
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return ""

    def load_documents(self):
        print("\nStarting document loading...")
        course_materials_path = "./data/course_materials"
        print(f"Looking for PDFs in: {os.path.abspath(course_materials_path)}")
        
        for root, _, files in os.walk(course_materials_path):
            for file in files:
                if file.endswith('.pdf'):
                    file_path = os.path.join(root, file)
                    print(f"\nProcessing PDF: {file}")
                    content = self.read_pdf(file_path)
                    if content:
                        print(f"Successfully loaded {file} - Content length: {len(content)}")
                        # Split content into smaller chunks
                        chunks = [content[i:i+1000] for i in range(0, len(content), 800)]  # 200 words overlap
                        for i, chunk in enumerate(chunks):
                            self.documents.append({
                                'content': chunk,
                                'source': file,
                                'path': file_path,
                                'chunk_id': i
                            })
        
        if self.documents:
            print(f"\nTotal chunks created: {len(self.documents)}")
            texts = [doc['content'] for doc in self.documents]
            self.vectors = self.vectorizer.fit_transform(texts)
            print("Vectors created successfully")
    
    def get_context(self, query, n_results=5):  # Increased n_results
        if not self.documents or self.vectors is None:
            return {'context': "", 'sources': []}
            
        try:
            # Get query vector
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.vectors)[0]
            
            # Set a higher similarity threshold for relevance
            similarity_threshold = 0.3  # Adjust as needed
            
            # Get top results that meet the similarity threshold
            top_indices = np.argsort(similarities)[::-1]
            top_indices = [idx for idx in top_indices if similarities[idx] >= similarity_threshold]
            
            context = ""
            sources = []
            seen_files = set()
            
            # Collect up to `n_results` relevant sources
            for idx in top_indices:
                if len(sources) >= n_results:
                    break
                doc = self.documents[idx]
                if doc['source'] not in seen_files:
                    context += f"\nFrom {doc['source']}:\n{doc['content']}\n"
                    sources.append({
                        'filename': doc['source'],
                        'similarity': float(similarities[idx])
                    })
                    seen_files.add(doc['source'])
            
            # If no relevant sources were found, return an empty response
            if not sources:
                print("No relevant sources found for the query.")
                return {'context': "No relevant content found.", 'sources': []}
            
            print(f"Found {len(sources)} relevant sources")
            return {
                'context': context.strip(),
                'sources': sources
            }
            
        except Exception as e:
            print(f"Error in get_context: {str(e)}")
            return {'context': "", 'sources': []}
