import os
import tempfile
import requests
from tqdm import tqdm
from moviepy.editor import VideoFileClip, AudioFileClip
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
import subprocess

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "https://api.openai.com/v1/audio/transcriptions")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

# --- Verify MoviePy and FFmpeg Setup ---
def verify_ffmpeg_setup():
    """Ensure FFmpeg and MoviePy are configured correctly."""
    try:
        print("Verifying FFmpeg installation...")
        result_ffmpeg = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result_ffmpeg.returncode == 0:
            print("FFmpeg is installed and working.")
        else:
            raise RuntimeError("FFmpeg not found. Please check your PATH or installation.")

        result_moviepy = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True)
        if result_moviepy.returncode == 0:
            print("FFprobe is installed and working.")
        else:
            raise RuntimeError("FFprobe not found. Please check your PATH or installation.")
    except Exception as e:
        raise RuntimeError(f"Error verifying FFmpeg/MoviePy setup: {e}")

# --- Initialize ChromaDB ---
def initialize_chromadb():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create the data directory if it doesn't exist
    data_dir = os.path.join(backend_dir, "data", "vector_store")
    os.makedirs(data_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=data_dir)
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

# --- Extract and Split Audio using MoviePy ---
def extract_and_split_audio_with_moviepy(video_path: str, chunk_duration: int = 900) -> list:
    """
    Extract audio from a video and split it into chunks using MoviePy.
    :param video_path: Path to the video file.
    :param chunk_duration: Duration of each audio chunk in seconds (default: 15 minutes).
    :return: List of paths to audio chunks.
    """
    print(f"Extracting audio from: {video_path}")
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "audio.mp3")

    try:
        # Extract audio from the video
        video = VideoFileClip(video_path)
        audio = video.audio
        if audio is None:
            raise ValueError("No audio found in the video.")
        audio.write_audiofile(audio_path, codec="mp3")
        print(f"Audio extracted successfully to: {audio_path}")

        # Split audio into chunks
        print("Splitting audio into chunks...")
        audio_clip = AudioFileClip(audio_path)
        duration = int(audio_clip.duration)

        chunks = []
        for start_time in range(0, duration, chunk_duration):
            chunk_path = os.path.join(temp_dir, f"chunk_{start_time}.mp3")
            audio_clip.subclip(start_time, min(start_time + chunk_duration, duration)).write_audiofile(chunk_path)
            chunks.append(chunk_path)
        print(f"Audio split into {len(chunks)} chunk(s).")
        return chunks
    except Exception as e:
        raise RuntimeError(f"Error processing audio: {e}")

# --- Transcribe Audio ---
def transcribe_audio_chunks(audio_chunks: list) -> str:
    """Send audio chunks to Whisper API and combine transcriptions."""
    transcriptions = []
    for chunk_path in tqdm(audio_chunks, desc="Transcribing audio chunks"):
        try:
            with open(chunk_path, "rb") as audio_file:
                files = {"file": ("audio.mp3", audio_file, "audio/mp3")}
                data = {"model": "whisper-1", "response_format": "text"}
                headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

                response = requests.post(WHISPER_API_URL, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    transcriptions.append(response.text)
                else:
                    print(f"Error: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Error processing chunk {chunk_path}: {e}")
    return " ".join(transcriptions)

# --- Process Video and Store in ChromaDB ---
def process_video_and_store(video_path: str, collection):
    """Extract audio, split it, transcribe, and store transcriptions in ChromaDB."""
    print(f"Processing video: {video_path}")
    audio_chunks = extract_and_split_audio_with_moviepy(video_path)
    transcription = transcribe_audio_chunks(audio_chunks)
    print("Transcription completed.")

    # Prepare metadata and store in ChromaDB
    video_name = os.path.basename(video_path)
    metadata = {"source": video_path, "filename": video_name}
    collection.add(documents=[transcription], metadatas=[metadata], ids=[video_name])
    print(f"Transcription stored for video: {video_name}")

# --- Process All Videos in Directory ---
def process_all_videos_in_directory(directory: str, collection):
    """Process all video files in the specified directory."""
    supported_formats = ('.mp4', '.avi', '.mov', '.mkv')
    video_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(supported_formats)]

    if not video_files:
        print(f"No video files found in directory: {directory}")
        return

    print(f"Found {len(video_files)} video(s) in the directory: {directory}")
    for video_file in tqdm(video_files, desc="Processing videos"):
        try:
            process_video_and_store(video_file, collection)
        except Exception as e:
            print(f"Error processing {video_file}: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # Directory containing videos
    video_directory = r"C:\Users\musku\Links\Pendrive\Shields course Fall 2024\class discussion videos"

    if not os.path.exists(video_directory):
        print(f"Directory not found: {video_directory}")
        exit(1)

    # Verify MoviePy and FFmpeg setup
    verify_ffmpeg_setup()

    # Initialize ChromaDB
    collection = initialize_chromadb()

    try:
        process_all_videos_in_directory(video_directory, collection)
        print("\nAll videos have been processed, and their transcriptions are saved in the vector store!")
    except Exception as e:
        print(f"Error: {e}")
