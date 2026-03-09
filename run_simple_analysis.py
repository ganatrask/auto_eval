#!/usr/bin/env python3
"""
Simple analysis: Did the robot pick and place the object?
Reads video IDs from JSON files in datasets/ folder.
"""

import json
from datetime import datetime
from pathlib import Path
from nomadicml import NomadicML
from nomadicml.video import AnalysisType

API_KEY = "sk_c6z5SmcEwunc89dVkrOU0LMu52vvWBKYBPMRqLpyuoCMFvAj"

QUERY = "Did the robot pick and place the object? Answer YES or NO, then explain briefly."

DATASET_FILES = [
    "datasets/front_cam.json",
    "datasets/real_robot_data.json",
    "datasets/workspace_cam.json",
]


def load_video_ids():
    """Load video IDs from dataset JSON files."""
    video_ids = []
    video_info = {}

    for filepath in DATASET_FILES:
        path = Path(filepath)
        if not path.exists():
            print(f"Warning: {filepath} not found, skipping...")
            continue

        with open(path) as f:
            data = json.load(f)

        dataset_name = path.stem  # e.g., "front_cam"
        for video in data.get("videos", []):
            vid = video["id"]
            video_ids.append(vid)
            video_info[vid] = {"title": video.get("title", ""), "dataset": dataset_name}

        print(f"Loaded {len(data.get('videos', []))} videos from {dataset_name}")

    return video_ids, video_info


def main():
    print("Loading video IDs from dataset files...")
    video_ids, video_info = load_video_ids()
    print(f"Total videos: {len(video_ids)}")

    print("Initializing NomadicML client...")
    client = NomadicML(api_key=API_KEY)

    print(f"Analyzing {len(video_ids)} videos...")

    # Run single query
    response = client.analyze(
        video_ids,
        analysis_type=AnalysisType.ASK,
        custom_event=QUERY,
    )

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "query": QUERY,
        "video_count": len(video_ids),
        "video_info": video_info,
        "response": response,
    }

    output_file = "simple_analysis_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Done! Results saved to: {output_file}")


if __name__ == "__main__":
    main()
