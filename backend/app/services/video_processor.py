import os
import requests
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import gc

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
whisper_api_url = os.getenv("WHISPER_API_URL")  # URL for Whisper API
video_materials_path = os.getenv("VIDEO_MATERIALS_PATH", "./data/video_materials")

def transcribe_video_with_api(file_path):
    """Transcribe video using Whisper API"""
    try:
        print(f"Starting to transcribe video: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")

        # Open the video file and send it to the Whisper API
        with open(file_path, "rb") as video_file:
            response = requests.post(
                whisper_api_url,
                headers={"Authorization": f"Bearer {openai_api_key}"},
                files={"file": video_file}
            )

        if response.status_code == 200:
            transcription = response.json().get("text", "")
            print(f"Transcription completed for {file_path}, length: {len(transcription)} characters")
            return transcription
        else:
            print(f"Failed to transcribe video {file_path}. Status code: {response.status_code}, Response: {response.text}")
            return None

    except Exception as e:
        print(f"Error transcribing video {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_video_directory(directory_path):
    """Process video files in a directory"""
    print(f"Starting to process directory: {directory_path}")

    # Get list of video files
    video_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                video_files.append(os.path.join(root, file))

    print(f"Found {len(video_files)} video files")
    all_transcriptions = []
    metadata = []

    for file_path in video_files:
        file_name = os.path.basename(file_path)
        print(f"\nProcessing video: {file_name}")

        try:
            transcription = transcribe_video_with_api(file_path)

            if transcription:
                all_transcriptions.append(transcription)
                metadata.append({
                    "source": file_path,
                    "filename": file_name,
                    "type": "video",
                    "transcription_length": len(transcription)
                })
                print(f"Successfully processed {file_name}")
                gc.collect()
            else:
                print(f"Skipped {file_name} - No transcription generated")

        except Exception as e:
            print(f"Error processing {file_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\nTotal processing complete. Generated {len(all_transcriptions)} transcriptions")
    return all_transcriptions, metadata

def main():
    print("Starting the process...")
    client = chromadb.PersistentClient(path="./data/vector_store")
    print("ChromaDB client initialized")

    print(f"Absolute path: {os.path.abspath(video_materials_path)}")
    print(f"Directory exists: {os.path.exists(video_materials_path)}")
    print(f"Is directory: {os.path.isdir(video_materials_path)}")

    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name="text-embedding-ada-002",
        dimensions=1536  # Explicitly set dimensions to avoid errors
    )
    print("OpenAI embedding function initialized")

    try:
        collection = client.get_collection(name="video_materials")
        print("Found existing collection")
    except:
        print("Creating new collection")
        collection = client.create_collection(
            name="video_materials",
            embedding_function=openai_ef,
            metadata={"description": "Video materials for RAG"}
        )

    print(f"Processing videos from: {video_materials_path}")

    try:
        transcriptions, metadata = process_video_directory(video_materials_path)

        if not transcriptions:
            print("No content was processed. Please check your files and directories.")
            return

        batch_size = 10
        total_batches = (len(transcriptions) - 1) // batch_size + 1

        print(f"\nStarting to add {len(transcriptions)} transcriptions to ChromaDB in {total_batches} batches")

        for i in range(0, len(transcriptions), batch_size):
            try:
                print(f"\nProcessing batch {i // batch_size + 1}/{total_batches}")
                batch_transcriptions = transcriptions[i:i + batch_size]
                batch_metadata = metadata[i:i + batch_size]
                batch_ids = [f"video_{j}" for j in range(i, i + len(batch_transcriptions))]

                collection.add(
                    documents=batch_transcriptions,
                    metadatas=batch_metadata,
                    ids=batch_ids
                )
                print(f"Successfully added batch {i // batch_size + 1}")
                gc.collect()

            except Exception as e:
                print(f"Error processing batch {i // batch_size + 1}: {e}")
                traceback.print_exc()
                continue

        print("\nProcessing completed successfully!")

    except Exception as e:
        print(f"An error occurred during processing: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()