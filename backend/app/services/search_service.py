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
            
            # Get top results
            top_indices = np.argsort(similarities)[-n_results*2:][::-1]  # Get more results initially
            
            context = ""
            sources = []
            seen_files = set()
            
            # First, prioritize files that match the topic
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Similarity threshold
                    doc = self.documents[idx]
                    if "metabolism" in doc['source'].lower() and doc['source'] not in seen_files:
                        context += f"\nFrom {doc['source']}:\n{doc['content']}\n"
                        sources.append({
                            'filename': doc['source'],
                            'similarity': float(similarities[idx])
                        })
                        seen_files.add(doc['source'])
            
            # If we haven't found enough relevant sources, add other high-scoring documents
            if len(sources) < n_results:
                for idx in top_indices:
                    if similarities[idx] > 0.1:  # Similarity threshold
                        doc = self.documents[idx]
                        if doc['source'] not in seen_files:
                            context += f"\nFrom {doc['source']}:\n{doc['content']}\n"
                            sources.append({
                                'filename': doc['source'],
                                'similarity': float(similarities[idx])
                            })
                            seen_files.add(doc['source'])
                            if len(sources) >= n_results:
                                break
            
            print(f"Found {len(sources)} relevant sources")
            return {
                'context': context.strip(),
                'sources': sources
            }
            
        except Exception as e:
            print(f"Error in get_context: {str(e)}")
            return {'context': "", 'sources': []}