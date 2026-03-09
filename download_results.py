#!/usr/bin/env python3
"""
Download existing analysis results from NomadicML platform.

This script retrieves previously computed analysis results without re-running analysis.

Based on official SDK docs: https://docs.nomadicml.com/api-reference/sdk-examples
"""

import os
import json
import argparse
from datetime import datetime
from typing import Optional

from nomadicml import NomadicML


class ResultsDownloader:
    """Download and manage analysis results from NomadicML."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with NomadicML client."""
        self.api_key = api_key or os.environ.get("NOMADICML_API_KEY")
        if not self.api_key:
            raise ValueError(
                "NomadicML API key required. Set NOMADICML_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = NomadicML(api_key=self.api_key)

    def list_videos(self, folder_name: Optional[str] = None, limit: Optional[int] = None) -> list[dict]:
        """List all videos, optionally filtered by folder.

        Uses: client.my_videos(folder_name)
        """
        if folder_name:
            print(f"Fetching videos from folder: {folder_name}")
        else:
            print("Fetching all videos...")
        try:
            videos = list(self.client.my_videos(folder_name))
            if limit:
                videos = videos[:limit]
            print(f"Found {len(videos)} videos")
            return videos
        except Exception as e:
            print(f"Error listing videos: {e}")
            return []

    def get_folder_info(self, folder_name: str) -> dict:
        """Get folder metadata.

        Uses: client.get_folder(name)
        """
        try:
            return self.client.get_folder(folder_name)
        except Exception as e:
            print(f"Error getting folder info: {e}")
            return {"error": str(e)}

    def get_batch_analysis(
        self,
        batch_id: str,
        filter_status: Optional[str] = None,
        as_csv: bool = False
    ) -> dict:
        """Get results for a completed batch analysis by batch_id.

        Uses: client.get_batch_analysis(batch_id, filter, as_csv)

        Args:
            batch_id: The batch ID returned when running analyze()
            filter_status: Filter by 'approved', 'rejected', 'pending', 'invalid'
            as_csv: Return CSV string instead of JSON
        """
        print(f"Fetching batch analysis: {batch_id}")
        try:
            results = self.client.get_batch_analysis(
                batch_id,
                filter=filter_status,
                as_csv=as_csv
            )
            return results
        except Exception as e:
            print(f"Error fetching batch {batch_id}: {e}")
            return {"error": str(e), "batch_id": batch_id}

    def get_visuals(self, video_id: str, analysis_id: Optional[str] = None) -> dict:
        """Get all thumbnail URLs for a video's analysis events.

        Uses: client.get_visuals(video_id, analysis_id)
        """
        print(f"Fetching visuals for video: {video_id}")
        try:
            return self.client.get_visuals(video_id, analysis_id)
        except Exception as e:
            print(f"Error fetching visuals for {video_id}: {e}")
            return {"error": str(e), "video_id": video_id}

    def search_events(
        self,
        query: str,
        folder_name: Optional[str] = None,
        scope: str = "user"
    ) -> dict:
        """Semantic search across analyzed events.

        Uses: client.search(query, folder_name, scope)

        Args:
            query: Natural language search query
            folder_name: Optional folder to search within
            scope: 'user' or 'org'
        """
        print(f"Searching for: {query}")
        try:
            return self.client.search(query, folder_name=folder_name, scope=scope)
        except Exception as e:
            print(f"Error searching: {e}")
            return {"error": str(e), "query": query}

    def get_video_analysis(self, video_id: str, analysis_id: Optional[str] = None) -> dict:
        """Get analysis results for a specific video.

        Uses: client.video.get_video_analysis(video_id, analysis_id)
        Note: This is an internal SDK method, may not be in public docs.
        """
        print(f"  Fetching analysis for video: {video_id}")
        try:
            results = self.client.video.get_video_analysis(video_id, analysis_id)
            return results
        except AttributeError:
            # Method doesn't exist, try search instead
            print(f"  get_video_analysis not available, using search...")
            return self.search_events(f"video_id:{video_id}")
        except Exception as e:
            print(f"  Error fetching results for {video_id}: {e}")
            return {"error": str(e), "video_id": video_id}

    def get_folder_results(self, folder_name: str, limit: Optional[int] = None) -> list[dict]:
        """Get video info for all videos in a folder."""
        print(f"Fetching videos from folder: {folder_name}")

        # Get folder info
        folder_info = self.get_folder_info(folder_name)
        if "error" not in folder_info:
            print(f"Folder: {folder_info.get('id')}, Videos: {folder_info.get('video_count')}")

        # Get all videos in folder
        videos = list(self.client.my_videos(folder_name))
        if limit:
            videos = videos[:limit]

        print(f"Found {len(videos)} videos")
        return videos

    def load_video_ids_from_json(self, json_files: list[str]) -> list[str]:
        """Load video IDs from JSON files."""
        from pathlib import Path

        video_ids = []
        for filepath in json_files:
            path = Path(filepath)
            if not path.exists():
                print(f"Warning: {filepath} not found, skipping...")
                continue

            with open(path) as f:
                data = json.load(f)

            for video in data.get("videos", []):
                video_ids.append(video["id"])

            print(f"Loaded {len(data.get('videos', []))} video IDs from {path.stem}")

        return video_ids

    def save_results(self, results, output_file: str):
        """Save results to JSON file."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_items": len(results) if isinstance(results, list) else 1,
            "results": results,
        }
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Download existing analysis results from NomadicML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all videos in your account
  python download_results.py --list-videos

  # List videos in a specific folder
  python download_results.py --list-videos --folder-filter my-folder

  # Get batch analysis results (requires batch_id from when you ran analyze())
  python download_results.py --batch-id abc123

  # Export batch results as CSV
  python download_results.py --batch-id abc123 --csv

  # Search for events across all analyzed videos
  python download_results.py --search "robot picking up object"

  # Get thumbnail URLs for a video
  python download_results.py --visuals video123
        """
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--list-videos",
        action="store_true",
        help="List all videos in your account",
    )
    mode_group.add_argument(
        "--batch-id",
        help="Get results for a batch analysis by batch ID (from analyze() response)",
    )
    mode_group.add_argument(
        "--search",
        help="Semantic search query across analyzed events",
    )
    mode_group.add_argument(
        "--visuals",
        metavar="VIDEO_ID",
        help="Get thumbnail URLs for a video's analysis events",
    )
    mode_group.add_argument(
        "--video-id",
        help="Get analysis for a specific video ID (uses internal SDK method)",
    )
    mode_group.add_argument(
        "--folder",
        help="List videos in a folder",
    )
    mode_group.add_argument(
        "--from-json",
        nargs="+",
        metavar="JSON_FILE",
        help="Load video IDs from JSON files and fetch their analyses",
    )

    # Common options
    parser.add_argument(
        "--api-key",
        help="NomadicML API key (or set NOMADICML_API_KEY env var)",
    )
    parser.add_argument(
        "--output", "-o",
        default="downloaded_results.json",
        help="Output JSON file (default: downloaded_results.json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of results to fetch",
    )
    parser.add_argument(
        "--folder-filter",
        help="Filter by folder name (for --list-videos and --search)",
    )
    parser.add_argument(
        "--analysis-id",
        help="Specific analysis ID (for --video-id and --visuals)",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output as CSV (for --batch-id mode)",
    )
    parser.add_argument(
        "--filter-status",
        choices=["approved", "rejected", "pending", "invalid"],
        help="Filter batch results by status (for --batch-id mode)",
    )

    args = parser.parse_args()

    # Initialize downloader
    downloader = ResultsDownloader(api_key=args.api_key)

    # Execute based on mode
    if args.list_videos:
        videos = downloader.list_videos(
            folder_name=args.folder_filter,
            limit=args.limit
        )
        print("\n" + "=" * 60)
        print("VIDEOS")
        print("=" * 60)
        for i, video in enumerate(videos, 1):
            video_id = video.get("video_id") or video.get("id")
            name = video.get("name") or video.get("filename") or "unnamed"
            print(f"  [{i}] {video_id} - {name}")

        downloader.save_results(videos, args.output)

    elif args.batch_id:
        result = downloader.get_batch_analysis(
            args.batch_id,
            filter_status=args.filter_status,
            as_csv=args.csv
        )

        print("\n" + "=" * 60)
        print(f"BATCH ANALYSIS: {args.batch_id}")
        print("=" * 60)

        if args.csv and isinstance(result, str):
            print(result)
            # Save as CSV file
            csv_output = args.output.replace(".json", ".csv")
            with open(csv_output, "w") as f:
                f.write(result)
            print(f"CSV saved to: {csv_output}")
        else:
            if "error" not in result:
                batch_meta = result.get("batch_metadata", {})
                results_list = result.get("results", [])
                print(f"  Status: {batch_meta.get('status', 'unknown')}")
                print(f"  Videos: {len(results_list)}")
            print(json.dumps(result, indent=2, default=str))
            downloader.save_results(result, args.output)

    elif args.search:
        result = downloader.search_events(
            args.search,
            folder_name=args.folder_filter
        )

        print("\n" + "=" * 60)
        print(f"SEARCH RESULTS: {args.search}")
        print("=" * 60)
        print(json.dumps(result, indent=2, default=str))

        downloader.save_results(result, args.output)

    elif args.visuals:
        result = downloader.get_visuals(args.visuals, args.analysis_id)

        print("\n" + "=" * 60)
        print(f"VISUALS FOR: {args.visuals}")
        print("=" * 60)
        print(json.dumps(result, indent=2, default=str))

        downloader.save_results(result, args.output)

    elif args.video_id:
        result = downloader.get_video_analysis(args.video_id, args.analysis_id)

        print("\n" + "=" * 60)
        print(f"ANALYSIS FOR: {args.video_id}")
        print("=" * 60)
        print(json.dumps(result, indent=2, default=str))

        downloader.save_results(result, args.output)

    elif args.folder:
        videos = downloader.get_folder_results(args.folder, limit=args.limit)

        print("\n" + "=" * 60)
        print(f"VIDEOS IN FOLDER: {args.folder}")
        print("=" * 60)
        for i, video in enumerate(videos, 1):
            video_id = video.get("video_id") or video.get("id")
            name = video.get("name") or video.get("filename") or "unnamed"
            print(f"  [{i}] {video_id} - {name}")

        downloader.save_results(videos, args.output)

    elif args.from_json:
        # Load video IDs from JSON files
        video_ids = downloader.load_video_ids_from_json(args.from_json)
        if args.limit:
            video_ids = video_ids[:args.limit]

        print(f"\nFetching analyses for {len(video_ids)} videos...")
        print("=" * 60)

        results = []
        for i, video_id in enumerate(video_ids, 1):
            print(f"[{i}/{len(video_ids)}] {video_id}")
            analysis = downloader.get_video_analysis(video_id, args.analysis_id)
            results.append({
                "video_id": video_id,
                "analysis": analysis,
            })

            # Save intermediate results every 10 videos
            if i % 10 == 0:
                downloader.save_results(results, args.output)
                print(f"  (saved intermediate results)")

        print("\n" + "=" * 60)
        print(f"FETCHED ANALYSES FOR {len(results)} VIDEOS")
        print("=" * 60)

        # Count successes and errors
        successes = sum(1 for r in results if "error" not in r.get("analysis", {}))
        errors = len(results) - successes
        print(f"  Successes: {successes}")
        print(f"  Errors: {errors}")

        downloader.save_results(results, args.output)


if __name__ == "__main__":
    main()
