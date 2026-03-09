#!/usr/bin/env python3
"""
Run batch analysis on videos already uploaded to NomadicML server.
Analyzes videos from: real_robot_data, front_cam, worspace_cam folders.
"""

import sys
import json
from datetime import datetime
from nomadicml import NomadicML
from nomadicml.video import AnalysisType

API_KEY = "sk_c6z5SmcEwunc89dVkrOU0LMu52vvWBKYBPMRqLpyuoCMFvAj"

EVALUATION_QUERIES = {
    "object_identification": (
        "Analyze this robot manipulation video. Identify the object being manipulated. "
        "Object type options: Cube, Rectangular box, Cylinder, Capsule. "
        "Color options: Red, Green, Blue, Yellow, Cyan, Magenta, Orange, Purple. "
        "Answer in format: TYPE: <object_type>, COLOR: <color>. "
        "Explain your reasoning."
    ),
    "grasp": (
        "Analyze this robot manipulation video. Did the robot successfully "
        "grasp and pick up the target object? Look for: gripper closing on object, "
        "object being lifted off the surface. Answer YES if successful grasp, NO if failed. "
        "Explain your reasoning."
    ),
    "transport": (
        "Analyze this robot manipulation video. Did the robot successfully "
        "transport/move the object without dropping it? Look for: stable grip during movement, "
        "no object slippage or drops. Answer YES if successful transport, NO if failed. "
        "Explain your reasoning."
    ),
    "place": (
        "Analyze this robot manipulation video. Did the robot successfully "
        "place the object at the target location? Look for: controlled release, "
        "object resting stably at destination. Answer YES if successful placement, NO if failed. "
        "Explain your reasoning."
    ),
    "overall": (
        "Analyze this robot pick-and-place video end-to-end. Was the complete task successful? "
        "The task involves: 1) picking up an object, 2) moving it, 3) placing it at target. "
        "Answer YES if the full task was completed successfully, NO if any step failed. "
        "Explain your reasoning."
    ),
    "failure_mode": (
        "If this robot pick-and-place attempt failed, identify the failure mode. "
        "Options: MISSED_GRASP (gripper missed object), DROPPED_OBJECT (object fell during transport), "
        "WRONG_PLACEMENT (placed in wrong location), COLLISION (hit obstacle), "
        "INCOMPLETE (task not finished), SUCCESS (no failure). "
        "State the failure mode and explain."
    ),
}

FOLDERS_TO_ANALYZE = ["real_robot_data", "front_cam", "worspace_cam"]


def run_batch_analysis(client, video_ids, query_name, query_text):
    """Run batch analysis on multiple videos."""
    print(f"      Sending request for {len(video_ids)} videos...", flush=True)
    try:
        response = client.analyze(
            video_ids,
            analysis_type=AnalysisType.ASK,
            custom_event=query_text,
        )
        print(f"      Response received!", flush=True)
        return response
    except Exception as e:
        print(f"      ERROR: {e}", flush=True)
        return None


def analyze_folder(client, folder_name, videos, output_prefix=""):
    """Analyze all videos in a folder."""
    print(f"\n{'='*60}", flush=True)
    print(f"ANALYZING FOLDER: {folder_name} ({len(videos)} videos)", flush=True)
    print(f"{'='*60}", flush=True)

    video_ids = [v["video_id"] for v in videos]
    results = {
        "folder": folder_name,
        "video_count": len(videos),
        "timestamp": datetime.now().isoformat(),
        "videos": {v["video_id"]: {"video_name": v["video_name"], "video_id": v["video_id"]} for v in videos},
        "analyses": {},
    }

    # Run each query type
    total_queries = len(EVALUATION_QUERIES)
    for i, (query_name, query_text) in enumerate(EVALUATION_QUERIES.items(), 1):
        print(f"\n  [{i}/{total_queries}] {query_name}", flush=True)
        response = run_batch_analysis(client, video_ids, query_name, query_text)
        if response:
            results["analyses"][query_name] = response
            print(f"      ✓ Completed", flush=True)
        else:
            print(f"      ✗ Failed", flush=True)

        # Save intermediate results
        output_file = f"{output_prefix}{folder_name}_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"      Saved to {output_file}", flush=True)

    return results


def main():
    # Parse arguments
    folders_to_run = FOLDERS_TO_ANALYZE
    if len(sys.argv) > 1:
        folders_to_run = sys.argv[1:]
        print(f"Running for specified folders: {folders_to_run}", flush=True)

    print("Initializing NomadicML client...", flush=True)
    client = NomadicML(api_key=API_KEY)

    # Get all videos
    print("Fetching video list...", flush=True)
    all_videos = client.my_videos()
    print(f"Total videos on server: {len(all_videos)}", flush=True)

    # Group by folder
    folders = {}
    for v in all_videos:
        folder = v.get("folder_name", "default")
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(v)

    print("\nFolders found:", flush=True)
    for folder, vids in sorted(folders.items()):
        marker = "→" if folder in folders_to_run else " "
        print(f"  {marker} {folder}: {len(vids)} videos", flush=True)

    # Analyze each target folder
    for folder_name in folders_to_run:
        if folder_name in folders:
            analyze_folder(client, folder_name, folders[folder_name])
        else:
            print(f"\nWARNING: Folder '{folder_name}' not found!", flush=True)

    print(f"\n{'='*60}", flush=True)
    print(f"ANALYSIS COMPLETE!", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
