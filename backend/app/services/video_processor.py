import os
import requests
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import gc
import logging
import sys
import time
import tempfile
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import moviepy.editor as mp
from pydub import AudioSegment
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_processing.log'),
        logging.StreamHandler()
    ]
)

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class VideoProcessor:
    def __init__(self):
        self._load_and_validate_env()
        self.supported_formats = ('.mp4', '.avi', '.mov', '.mkv')
        self.chroma_client = None
        self.collection = None
        self.openai_ef = None
        self.chunk_length = 15 * 60 * 1000  # 15 minutes in milliseconds
        self.max_chunk_size = 25 * 1024 * 1024  # 25MB in bytes

    def _load_and_validate_env(self):
        """Load and validate environment variables"""
        load_dotenv()
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.whisper_api_url = os.getenv("WHISPER_API_URL")
        self.video_materials_path = os.getenv("VIDEO_MATERIALS_PATH", "./data/video_materials")

        missing_vars = []
        if not self.openai_api_key:
            missing_vars.append("OPENAI_API_KEY")
        if not self.whisper_api_url:
            missing_vars.append("WHISPER_API_URL")

        if missing_vars:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please ensure these are set in your .env file:\n"
                f"OPENAI_API_KEY=your_api_key\n"
                f"WHISPER_API_URL=https://api.openai.com/v1/audio/transcriptions"
            )

        if not self.whisper_api_url.startswith(('http://', 'https://')):
            raise ConfigurationError(
                f"Invalid WHISPER_API_URL: {self.whisper_api_url}\n"
                f"URL must start with http:// or https://"
            )

        if not os.path.exists(self.video_materials_path):
            raise ConfigurationError(
                f"Video materials path does not exist: {self.video_materials_path}"
            )

    def verify_api_setup(self):
        """Verify API configuration"""
        logging.info("Verifying API Configuration:")
        logging.info(f"Whisper API URL: {self.whisper_api_url}")
        logging.info(f"API Key (first 4 chars): {self.openai_api_key[:4] if self.openai_api_key else 'None'}")
        
        try:
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self.openai_api_key}"}
            )
            if response.status_code == 200:
                logging.info("Successfully connected to OpenAI API")
            else:
                logging.error(f"Failed to connect to OpenAI API. Status code: {response.status_code}")
        except Exception as e:
            logging.error(f"Error connecting to OpenAI API: {e}")

    def initialize_chroma(self) -> None:
        """Initialize ChromaDB client and collection"""
        try:
            self.chroma_client = chromadb.PersistentClient(path="./data/vector_store")
            logging.info("ChromaDB client initialized")

            self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.openai_api_key,
                model_name="text-embedding-ada-002",
                dimensions=1536
            )
            
            try:
                self.collection = self.chroma_client.get_collection(name="video_materials")
                logging.info("Found existing collection")
            except:
                logging.info("Creating new collection")
                self.collection = self.chroma_client.create_collection(
                    name="video_materials",
                    embedding_function=self.openai_ef,
                    metadata={"description": "Video materials for RAG"}
                )
        except Exception as e:
            logging.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def extract_and_transcribe_audio(self, video_path: str) -> Optional[str]:
        """Extract audio from video and transcribe in chunks"""
        try:
            logging.info(f"Extracting audio from video: {video_path}")
            
            # Extract audio using moviepy
            video = mp.VideoFileClip(video_path)
            
            # Create a temporary directory for audio files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Export audio to temporary file
                temp_audio_path = f"{temp_dir}/temp_audio.mp3"
                video.audio.write_audiofile(temp_audio_path, codec='mp3', logger=None)
                video.close()
                
                # Load audio file using pydub
                audio = AudioSegment.from_mp3(temp_audio_path)
                
                # Split audio into chunks
                chunks = []
                for i in range(0, len(audio), self.chunk_length):
                    chunk = audio[i:i + self.chunk_length]
                    chunk_path = f"{temp_dir}/chunk_{i}.mp3"
                    chunk.export(chunk_path, format="mp3")
                    chunks.append(chunk_path)
                
                # Transcribe each chunk with progress bar
                transcriptions = []
                with tqdm(total=len(chunks), desc="Transcribing chunks") as pbar:
                    for chunk_path in chunks:
                        if os.path.getsize(chunk_path) > self.max_chunk_size:
                            logging.warning(f"Chunk too large, skipping: {chunk_path}")
                            continue
                        
                        transcription = self._transcribe_audio_chunk(chunk_path)
                        if transcription:
                            transcriptions.append(transcription)
                        pbar.update(1)
                
                # Combine all transcriptions
                return " ".join(transcriptions)
                
        except Exception as e:
            logging.error(f"Error processing video {video_path}: {e}")
            return None

    def _transcribe_audio_chunk(self, audio_path: str) -> Optional[str]:
        """Transcribe a single audio chunk"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                with open(audio_path, "rb") as audio_file:
                    files = {
                        "file": ("audio.mp3", audio_file, "audio/mp3")
                    }
                    data = {
                        "model": "whisper-1",
                        "response_format": "json"
                    }
                    
                    response = requests.post(
                        self.whisper_api_url,
                        headers={"Authorization": f"Bearer {self.openai_api_key}"},
                        files=files,
                        data=data,
                        timeout=300
                    )

                if response.status_code == 200:
                    return response.json().get("text", "")
                else:
                    logging.error(f"Failed to transcribe chunk. Status: {response.status_code}")
                    if response.status_code == 429 and attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    return None

            except Exception as e:
                logging.error(f"Error transcribing chunk: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
        
        return None

    def get_video_files(self) -> List[str]:
        """Get list of video files from directory"""
        video_files = []
        for file_path in Path(self.video_materials_path).rglob("*"):
            if file_path.suffix.lower() in self.supported_formats:
                video_files.append(str(file_path))
        logging.info(f"Found {len(video_files)} video files")
        return video_files

    def process_video(self, file_path: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Process a single video file"""
        file_name = os.path.basename(file_path)
        try:
            transcription = self.extract_and_transcribe_audio(file_path)
            if transcription:
                metadata = {
                    "source": file_path,
                    "filename": file_name,
                    "type": "video",
                    "transcription_length": len(transcription),
                    "processed_date": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                return transcription, metadata
            return None, None
        except Exception as e:
            logging.error(f"Error processing {file_name}: {e}")
            return None, None

    def process_videos_parallel(self, max_workers: int = 3) -> Tuple[List[str], List[Dict]]:
        """Process videos in parallel"""
        video_files = self.get_video_files()
        all_transcriptions = []
        all_metadata = []

        with tqdm(total=len(video_files), desc="Processing videos") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for transcription, metadata in executor.map(self.process_video, video_files):
                    if transcription and metadata:
                        all_transcriptions.append(transcription)
                        all_metadata.append(metadata)
                    pbar.update(1)

        return all_transcriptions, all_metadata

    def store_in_chroma(self, transcriptions: List[str], metadata: List[Dict]) -> None:
        """Store transcriptions in ChromaDB with batching"""
        if not transcriptions:
            logging.warning("No content to store in ChromaDB")
            return

        batch_size = 10
        total_batches = (len(transcriptions) - 1) // batch_size + 1

        with tqdm(total=total_batches, desc="Storing in ChromaDB") as pbar:
            for i in range(0, len(transcriptions), batch_size):
                try:
                    batch_transcriptions = transcriptions[i:i + batch_size]
                    batch_metadata = metadata[i:i + batch_size]
                    batch_ids = [f"video_{j}" for j in range(i, i + len(batch_transcriptions))]

                    self.collection.add(
                        documents=batch_transcriptions,
                        metadatas=batch_metadata,
                        ids=batch_ids
                    )
                    gc.collect()
                    pbar.update(1)

                except Exception as e:
                    logging.error(f"Error processing batch {i // batch_size + 1}: {e}")
                    continue

    def run(self) -> None:
        """Main execution method"""
        try:
            self.verify_api_setup()
            self.initialize_chroma()
            transcriptions, metadata = self.process_videos_parallel()
            self.store_in_chroma(transcriptions, metadata)
            logging.info("Processing completed successfully!")
        except ConfigurationError as e:
            logging.error(f"Configuration error: {e}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"An error occurred during processing: {e}")
            raise

def main():
    try:
        processor = VideoProcessor()
        processor.run()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()