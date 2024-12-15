import os
import requests
import tempfile
from tqdm import tqdm
from moviepy.video.io.VideoFileClip import VideoFileClip
from dotenv import load_dotenv
from pydub import AudioSegment
import chromadb
from chromadb.utils import embedding_functions

# Explicitly set the path to FFmpeg and FFprobe for pydub
#AudioSegment.converter = r"C:\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe"
#AudioSegment.ffprobe = r"C:\ffmpeg-7.1-essentials_build\bin\ffprobe.exe"

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "https://api.openai.com/v1/audio/transcriptions")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

def initialize_chromadb():
    client = chromadb.PersistentClient(path="./data/vector_store")
    openai_embedding = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-ada-002",
        dimensions=1536
    )
    try:
        collection = client.get_collection(name="video_transcriptions")
    except Exception:
        collection = client.create_collection(
            name="video_transcriptions",
            embedding_function=openai_embedding
        )
    return collection

def extract_audio_with_moviepy(video_path: str) -> str:
    """Extract audio from video using MoviePy."""
    print(f"Extracting audio from: {video_path}")
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "audio.mp3")
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path, logger=None)  # Fixed: Removed verbose
        video.close()
        return audio_path
    except Exception as e:
        raise RuntimeError(f"Error extracting audio: {e}")

def split_audio(audio_path: str, max_size: int = 25 * 1024 * 1024) -> list:
    print(f"Splitting audio file: {audio_path}")
    audio = AudioSegment.from_file(audio_path)
    chunk_length = 15 * 60 * 1000  # 15 minutes in milliseconds

    chunks = []
    temp_dir = tempfile.mkdtemp()

    for i in range(0, len(audio), chunk_length):
        chunk = audio[i:i + chunk_length]
        chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp3")

        # Export the chunk
        chunk.export(chunk_path, format="mp3")

        # Check file size
        if os.path.getsize(chunk_path) > max_size:
            print(f"Chunk {chunk_path} exceeds size limit. Reducing chunk size further.")
            chunks += split_audio(chunk_path, max_size)
        else:
            chunks.append(chunk_path)

    return chunks

def transcribe_audio_chunks(audio_chunks: list) -> str:
    print("Transcribing audio chunks...")
    transcriptions = []

    for chunk_path in tqdm(audio_chunks, desc="Transcribing chunks"):
        try:
            with open(chunk_path, "rb") as audio_file:
                files = {"file": ("audio.mp3", audio_file, "audio/mp3")}
                data = {"model": "whisper-1", "response_format": "text"}
                headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

                response = requests.post(WHISPER_API_URL, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    transcriptions.append(response.text)
                else:
                    print(f"Error transcribing chunk {chunk_path}: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Error processing chunk {chunk_path}: {e}")

    return " ".join(transcriptions)

def process_video_and_store(video_path: str, collection):
    print(f"Processing video: {video_path}")
    audio_path = extract_audio_with_moviepy(video_path)

    # Split audio into chunks
    audio_chunks = split_audio(audio_path)

    # Transcribe the chunks and combine
    transcription = transcribe_audio_chunks(audio_chunks)
    print("Transcription completed.")

    # Prepare metadata
    video_name = os.path.basename(video_path)
    metadata = {"source": video_path, "filename": video_name}

    collection.add(
        documents=[transcription],
        metadatas=[metadata],
        ids=[video_name]
    )
    print(f"Transcription stored in vector store for video: {video_name}")

def process_all_videos_in_directory(directory: str, collection):
    supported_formats = ('.mp4', '.avi', '.mov', '.mkv')
    video_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(supported_formats)]

    if not video_files:
        print(f"No video files found in the directory: {directory}")
        return

    print(f"Found {len(video_files)} video(s) in the directory: {directory}")

    for video_file in tqdm(video_files, desc="Processing videos"):
        try:
            process_video_and_store(video_file, collection)
        except Exception as e:
            print(f"Error processing {video_file}: {e}")

if __name__ == "__main__":
    video_directory = r"C:\Users\musku\Links\Pendrive\Shields course Fall 2024\class discussion videos"

    if not os.path.exists(video_directory):
        print(f"Directory not found: {video_directory}")
        exit(1)

    collection = initialize_chromadb()

    try:
        process_all_videos_in_directory(video_directory, collection)
        print("\nAll videos have been processed, and their transcriptions are saved in the vector store!")
    except Exception as e:
        print(f"Error: {e}")
