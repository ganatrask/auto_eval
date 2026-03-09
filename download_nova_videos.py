#!/usr/bin/env python3
"""
Download all videos from the ganatrask/NOVA HuggingFace dataset.
"""

from huggingface_hub import snapshot_download, HfApi
import os

def download_nova_videos(output_dir="nova_videos"):
    """Download all videos from the NOVA dataset."""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    print("Downloading videos from ganatrask/NOVA dataset...")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    print("-" * 50)

    # Download only the videos folder from the dataset
    local_dir = snapshot_download(
        repo_id="ganatrask/NOVA",
        repo_type="dataset",
        allow_patterns="videos/**",  # Only download files in videos folder
        local_dir=output_dir,
    )

    print("-" * 50)
    print(f"Download complete! Videos saved to: {local_dir}")

    # List downloaded files
    video_dir = os.path.join(local_dir, "videos")
    if os.path.exists(video_dir):
        total_files = 0
        for root, dirs, files in os.walk(video_dir):
            for f in files:
                total_files += 1
                filepath = os.path.join(root, f)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                rel_path = os.path.relpath(filepath, video_dir)
                print(f"  {rel_path} ({size_mb:.2f} MB)")
        print(f"\nTotal video files downloaded: {total_files}")

    return local_dir

if __name__ == "__main__":
    download_nova_videos()
