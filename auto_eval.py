#!/usr/bin/env python3
"""
Auto-evaluation of pick-and-place robotics episodes using NomadicML API.

This module analyzes robot manipulation videos to evaluate:
- Grasp success/failure
- Object transport quality
- Placement accuracy
- Overall task completion
"""

import os
import json
import glob
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

from nomadicml import NomadicML
from nomadicml.video import AnalysisType


@dataclass
class EvaluationResult:
    """Result of evaluating a single episode."""
    episode_id: str
    video_path: str
    video_id: Optional[str] = None
    object_type: Optional[str] = None
    object_color: Optional[str] = None
    object_analysis: Optional[str] = None
    grasp_success: Optional[bool] = None
    grasp_analysis: Optional[str] = None
    transport_success: Optional[bool] = None
    transport_analysis: Optional[str] = None
    place_success: Optional[bool] = None
    place_analysis: Optional[str] = None
    overall_success: Optional[bool] = None
    overall_analysis: Optional[str] = None
    failure_mode: Optional[str] = None
    raw_responses: Optional[dict] = None
    error: Optional[str] = None


class PickPlaceEvaluator:
    """Evaluator for pick-and-place robotics episodes using NomadicML."""

    # Evaluation queries for pick-and-place tasks
    # Object types and colors to identify
    OBJECT_TYPES = ["Cube", "Rectangular box", "Cylinder", "Capsule"]
    OBJECT_COLORS = ["Red", "Green", "Blue", "Yellow", "Cyan", "Magenta", "Orange", "Purple"]

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

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the evaluator with NomadicML client."""
        self.api_key = api_key or os.environ.get("NOMADICML_API_KEY")
        if not self.api_key:
            raise ValueError(
                "NomadicML API key required. Set NOMADICML_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = NomadicML(api_key=self.api_key)
        self.uploaded_videos: dict[str, str] = {}  # path -> video_id mapping

    def upload_video(self, video_path: str) -> str:
        """Upload a single video and return its video_id."""
        if video_path in self.uploaded_videos:
            print(f"  Using cached video_id for {video_path}")
            return self.uploaded_videos[video_path]

        print(f"  Uploading {video_path}...")
        response = self.client.upload(video_path)
        video_id = response["video_id"]
        self.uploaded_videos[video_path] = video_id
        print(f"  Uploaded: video_id={video_id}")
        return video_id

    def upload_videos_batch(self, video_paths: list[str], folder: Optional[str] = None) -> list[str]:
        """Upload multiple videos in batch."""
        print(f"Uploading {len(video_paths)} videos...")

        # Filter out already uploaded videos
        new_paths = [p for p in video_paths if p not in self.uploaded_videos]

        if new_paths:
            if folder:
                responses = self.client.upload(new_paths, folder=folder)
            else:
                responses = self.client.upload(new_paths)

            # Handle both single and batch response formats
            if isinstance(responses, dict):
                responses = [responses]

            for path, resp in zip(new_paths, responses):
                self.uploaded_videos[path] = resp["video_id"]
                print(f"  Uploaded: {os.path.basename(path)} -> {resp['video_id']}")

        return [self.uploaded_videos[p] for p in video_paths]

    def analyze_video(self, video_id: str, query: str) -> dict:
        """Run a single analysis query on a video."""
        response = self.client.analyze(
            video_id,
            analysis_type=AnalysisType.ASK,
            custom_event=query,
        )
        return response

    def analyze_batch(self, video_ids: list[str], query: str) -> dict:
        """Run batch analysis on multiple videos."""
        response = self.client.analyze(
            video_ids,
            analysis_type=AnalysisType.ASK,
            custom_event=query,
        )
        return response

    def analyze_folder(self, folder_name: str, query: str) -> dict:
        """Run analysis on all videos in a folder."""
        response = self.client.analyze(
            folder=folder_name,
            analysis_type=AnalysisType.ASK,
            custom_event=query,
        )
        return response

    def get_folder_videos(self, folder_name: str) -> list[dict]:
        """Get all videos from a folder."""
        videos = list(self.client.my_videos(folder_name))
        return videos

    def load_video_ids_from_json(self, json_files: list[str]) -> tuple[list[str], dict]:
        """Load video IDs from JSON files exported from NomadicML."""
        from pathlib import Path

        video_ids = []
        video_info = {}

        for filepath in json_files:
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
                video_info[vid] = {
                    "title": video.get("title", ""),
                    "filename": video.get("filename", ""),
                    "dataset": dataset_name,
                }

            print(f"Loaded {len(data.get('videos', []))} videos from {dataset_name}")

        return video_ids, video_info

    def evaluate_from_json(
        self,
        json_files: list[str],
        output_file: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[EvaluationResult]:
        """Evaluate videos using IDs from JSON files."""
        print("\nLoading video IDs from JSON files...")
        video_ids, video_info = self.load_video_ids_from_json(json_files)

        if limit:
            video_ids = video_ids[:limit]

        print(f"Total videos to analyze: {len(video_ids)}")
        print("-" * 50)

        # Initialize results
        results = []
        for vid in video_ids:
            info = video_info.get(vid, {})
            episode_id = info.get("title") or info.get("filename") or vid
            results.append(EvaluationResult(
                episode_id=episode_id,
                video_path=info.get("filename", ""),
                video_id=vid,
                raw_responses={},
            ))

        # Run batch analysis for each query type
        print("\n" + "=" * 50)
        print("Running batch analysis...")
        print("=" * 50)

        for query_name, query_text in self.EVALUATION_QUERIES.items():
            if query_name == "failure_mode":
                continue

            print(f"\n  Analyzing: {query_name}...")
            try:
                batch_response = self.analyze_batch(video_ids, query_text)

                # Parse batch results
                batch_results = batch_response.get("results", [])
                for batch_result in batch_results:
                    vid = batch_result.get("video_id")
                    for result in results:
                        if result.video_id == vid:
                            result.raw_responses[query_name] = batch_result

                            if query_name == "object_identification":
                                result.object_type = self.parse_object_type(batch_result)
                                result.object_color = self.parse_object_color(batch_result)
                                result.object_analysis = str(batch_result)
                            elif query_name == "grasp":
                                result.grasp_success = self.parse_yes_no(batch_result)
                                result.grasp_analysis = str(batch_result)
                            elif query_name == "transport":
                                result.transport_success = self.parse_yes_no(batch_result)
                                result.transport_analysis = str(batch_result)
                            elif query_name == "place":
                                result.place_success = self.parse_yes_no(batch_result)
                                result.place_analysis = str(batch_result)
                            elif query_name == "overall":
                                result.overall_success = self.parse_yes_no(batch_result)
                                result.overall_analysis = str(batch_result)
                            break

            except Exception as e:
                print(f"    ERROR in {query_name}: {e}")

        # Run failure mode analysis for failed episodes
        print("\n  Analyzing failure modes for failed episodes...")
        failed_ids = [r.video_id for r in results if r.overall_success is False]
        if failed_ids:
            try:
                failure_response = self.analyze_batch(failed_ids, self.EVALUATION_QUERIES["failure_mode"])
                for batch_result in failure_response.get("results", []):
                    vid = batch_result.get("video_id")
                    for result in results:
                        if result.video_id == vid:
                            result.raw_responses["failure_mode"] = batch_result
                            result.failure_mode = self.parse_failure_mode(batch_result)
                            break
            except Exception as e:
                print(f"    ERROR in failure mode analysis: {e}")

        # Set SUCCESS for successful episodes
        for result in results:
            if result.overall_success is True:
                result.failure_mode = "SUCCESS"

        # Save results
        if output_file:
            self._save_results(results, output_file)

        return results

    def evaluate_from_folder(
        self,
        folder_name: str,
        output_file: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[EvaluationResult]:
        """Evaluate videos from an existing NomadicML folder."""
        print(f"\nFetching videos from folder: {folder_name}")

        # Get folder info
        folder_info = self.client.get_folder(folder_name)
        print(f"Folder: {folder_info.get('id')}, Videos: {folder_info.get('video_count')}")

        # Get all videos in folder
        videos = self.get_folder_videos(folder_name)

        if limit:
            videos = videos[:limit]

        print(f"Processing {len(videos)} videos")
        print("-" * 50)

        # Initialize results
        results = []
        video_ids = []
        for video in videos:
            video_id = video.get("video_id") or video.get("id")
            video_ids.append(video_id)
            episode_id = video.get("name") or video_id
            results.append(EvaluationResult(
                episode_id=episode_id,
                video_path=video.get("path", ""),
                video_id=video_id,
                raw_responses={},
            ))

        # Run batch analysis for each query type
        print("\n" + "=" * 50)
        print("Running batch analysis on folder...")
        print("=" * 50)

        for query_name, query_text in self.EVALUATION_QUERIES.items():
            if query_name == "failure_mode":
                continue

            print(f"\n  Analyzing: {query_name}...")
            try:
                # Use folder-based analysis
                batch_response = self.analyze_folder(folder_name, query_text)

                # Parse batch results
                batch_results = batch_response.get("results", [])
                for batch_result in batch_results:
                    vid = batch_result.get("video_id")
                    for result in results:
                        if result.video_id == vid:
                            result.raw_responses[query_name] = batch_result

                            if query_name == "object_identification":
                                result.object_type = self.parse_object_type(batch_result)
                                result.object_color = self.parse_object_color(batch_result)
                                result.object_analysis = str(batch_result)
                            elif query_name == "grasp":
                                result.grasp_success = self.parse_yes_no(batch_result)
                                result.grasp_analysis = str(batch_result)
                            elif query_name == "transport":
                                result.transport_success = self.parse_yes_no(batch_result)
                                result.transport_analysis = str(batch_result)
                            elif query_name == "place":
                                result.place_success = self.parse_yes_no(batch_result)
                                result.place_analysis = str(batch_result)
                            elif query_name == "overall":
                                result.overall_success = self.parse_yes_no(batch_result)
                                result.overall_analysis = str(batch_result)
                            break

            except Exception as e:
                print(f"    ERROR in {query_name}: {e}")

        # Run failure mode analysis for failed episodes
        print("\n  Analyzing failure modes for failed episodes...")
        failed_ids = [r.video_id for r in results if r.overall_success is False]
        if failed_ids:
            try:
                failure_response = self.analyze_batch(failed_ids, self.EVALUATION_QUERIES["failure_mode"])
                for batch_result in failure_response.get("results", []):
                    vid = batch_result.get("video_id")
                    for result in results:
                        if result.video_id == vid:
                            result.raw_responses["failure_mode"] = batch_result
                            result.failure_mode = self.parse_failure_mode(batch_result)
                            break
            except Exception as e:
                print(f"    ERROR in failure mode analysis: {e}")

        # Set SUCCESS for successful episodes
        for result in results:
            if result.overall_success is True:
                result.failure_mode = "SUCCESS"

        # Save results
        if output_file:
            self._save_results(results, output_file)

        return results

    def parse_yes_no(self, response: dict) -> Optional[bool]:
        """Parse a YES/NO response from the analysis."""
        # Extract text from response - adjust based on actual API response format
        text = str(response).upper()
        if "YES" in text:
            return True
        elif "NO" in text:
            return False
        return None

    def parse_failure_mode(self, response: dict) -> str:
        """Parse failure mode from the analysis response."""
        text = str(response).upper()
        modes = ["MISSED_GRASP", "DROPPED_OBJECT", "WRONG_PLACEMENT", "COLLISION", "INCOMPLETE", "SUCCESS"]
        for mode in modes:
            if mode in text:
                return mode
        return "UNKNOWN"

    def parse_object_type(self, response: dict) -> Optional[str]:
        """Parse object type from the analysis response."""
        text = str(response).upper()
        for obj_type in self.OBJECT_TYPES:
            if obj_type.upper() in text:
                return obj_type
        return None

    def parse_object_color(self, response: dict) -> Optional[str]:
        """Parse object color from the analysis response."""
        text = str(response).upper()
        for color in self.OBJECT_COLORS:
            if color.upper() in text:
                return color
        return None

    def evaluate_episode(self, video_path: str, episode_id: Optional[str] = None) -> EvaluationResult:
        """Evaluate a single episode video."""
        if episode_id is None:
            episode_id = os.path.splitext(os.path.basename(video_path))[0]

        result = EvaluationResult(
            episode_id=episode_id,
            video_path=video_path,
            raw_responses={},
        )

        try:
            # Upload video
            video_id = self.upload_video(video_path)
            result.video_id = video_id

            # Run all evaluation queries
            print(f"  Analyzing episode {episode_id}...")

            # Object identification
            print("    - Identifying object type and color...")
            object_resp = self.analyze_video(video_id, self.EVALUATION_QUERIES["object_identification"])
            result.raw_responses["object_identification"] = object_resp
            result.object_type = self.parse_object_type(object_resp)
            result.object_color = self.parse_object_color(object_resp)
            result.object_analysis = str(object_resp)

            # Grasp evaluation
            print("    - Evaluating grasp...")
            grasp_resp = self.analyze_video(video_id, self.EVALUATION_QUERIES["grasp"])
            result.raw_responses["grasp"] = grasp_resp
            result.grasp_success = self.parse_yes_no(grasp_resp)
            result.grasp_analysis = str(grasp_resp)

            # Transport evaluation
            print("    - Evaluating transport...")
            transport_resp = self.analyze_video(video_id, self.EVALUATION_QUERIES["transport"])
            result.raw_responses["transport"] = transport_resp
            result.transport_success = self.parse_yes_no(transport_resp)
            result.transport_analysis = str(transport_resp)

            # Placement evaluation
            print("    - Evaluating placement...")
            place_resp = self.analyze_video(video_id, self.EVALUATION_QUERIES["place"])
            result.raw_responses["place"] = place_resp
            result.place_success = self.parse_yes_no(place_resp)
            result.place_analysis = str(place_resp)

            # Overall evaluation
            print("    - Evaluating overall success...")
            overall_resp = self.analyze_video(video_id, self.EVALUATION_QUERIES["overall"])
            result.raw_responses["overall"] = overall_resp
            result.overall_success = self.parse_yes_no(overall_resp)
            result.overall_analysis = str(overall_resp)

            # Failure mode (only if not successful)
            if result.overall_success is False:
                print("    - Identifying failure mode...")
                failure_resp = self.analyze_video(video_id, self.EVALUATION_QUERIES["failure_mode"])
                result.raw_responses["failure_mode"] = failure_resp
                result.failure_mode = self.parse_failure_mode(failure_resp)
            else:
                result.failure_mode = "SUCCESS" if result.overall_success else None

        except Exception as e:
            result.error = str(e)
            print(f"    ERROR: {e}")

        return result

    def evaluate_dataset(
        self,
        video_dir: str,
        pattern: str = "*.mp4",
        limit: Optional[int] = None,
        output_file: Optional[str] = None,
        batch_mode: bool = False,
        folder: Optional[str] = None,
    ) -> list[EvaluationResult]:
        """Evaluate all videos in a directory.

        Args:
            video_dir: Directory containing video files
            pattern: Glob pattern for video files
            limit: Maximum number of videos to evaluate
            output_file: Output JSON file for results
            batch_mode: If True, upload all videos first then analyze in batch
            folder: Folder name for organizing uploads in NomadicML
        """
        # Find all video files
        search_pattern = os.path.join(video_dir, "**", pattern)
        video_paths = sorted(glob.glob(search_pattern, recursive=True))

        if limit:
            video_paths = video_paths[:limit]

        print(f"Found {len(video_paths)} videos to evaluate")
        print("-" * 50)

        if batch_mode:
            return self._evaluate_batch(video_paths, output_file, folder)
        else:
            return self._evaluate_sequential(video_paths, output_file)

    def _evaluate_sequential(
        self,
        video_paths: list[str],
        output_file: Optional[str] = None,
    ) -> list[EvaluationResult]:
        """Evaluate videos one by one (original behavior)."""
        results = []
        for i, video_path in enumerate(video_paths, 1):
            print(f"\n[{i}/{len(video_paths)}] Processing {os.path.basename(video_path)}")
            result = self.evaluate_episode(video_path)
            results.append(result)

            # Save intermediate results
            if output_file:
                self._save_results(results, output_file)

        return results

    def _evaluate_batch(
        self,
        video_paths: list[str],
        output_file: Optional[str] = None,
        folder: Optional[str] = None,
    ) -> list[EvaluationResult]:
        """Upload all videos first, then analyze in batch."""
        # Step 1: Batch upload all videos
        print("\n" + "=" * 50)
        print("STEP 1: Batch uploading videos...")
        print("=" * 50)
        video_ids = self.upload_videos_batch(video_paths, folder=folder)

        # Initialize results
        results = []
        for video_path, video_id in zip(video_paths, video_ids):
            episode_id = os.path.splitext(os.path.basename(video_path))[0]
            results.append(EvaluationResult(
                episode_id=episode_id,
                video_path=video_path,
                video_id=video_id,
                raw_responses={},
            ))

        # Step 2: Run batch analysis for each query type
        print("\n" + "=" * 50)
        print("STEP 2: Running batch analysis...")
        print("=" * 50)

        for query_name, query_text in self.EVALUATION_QUERIES.items():
            # Skip failure_mode for now - we'll run it selectively later
            if query_name == "failure_mode":
                continue

            print(f"\n  Analyzing: {query_name}...")
            try:
                batch_response = self.analyze_batch(video_ids, query_text)

                # Parse batch results
                batch_results = batch_response.get("results", [])
                for batch_result in batch_results:
                    vid = batch_result.get("video_id")
                    # Find matching result
                    for result in results:
                        if result.video_id == vid:
                            result.raw_responses[query_name] = batch_result

                            if query_name == "object_identification":
                                result.object_type = self.parse_object_type(batch_result)
                                result.object_color = self.parse_object_color(batch_result)
                                result.object_analysis = str(batch_result)
                            elif query_name == "grasp":
                                result.grasp_success = self.parse_yes_no(batch_result)
                                result.grasp_analysis = str(batch_result)
                            elif query_name == "transport":
                                result.transport_success = self.parse_yes_no(batch_result)
                                result.transport_analysis = str(batch_result)
                            elif query_name == "place":
                                result.place_success = self.parse_yes_no(batch_result)
                                result.place_analysis = str(batch_result)
                            elif query_name == "overall":
                                result.overall_success = self.parse_yes_no(batch_result)
                                result.overall_analysis = str(batch_result)
                            break

            except Exception as e:
                print(f"    ERROR in batch {query_name}: {e}")

        # Step 3: Run failure mode analysis for failed episodes
        print("\n  Analyzing failure modes for failed episodes...")
        failed_ids = [r.video_id for r in results if r.overall_success is False]
        if failed_ids:
            try:
                failure_response = self.analyze_batch(failed_ids, self.EVALUATION_QUERIES["failure_mode"])
                for batch_result in failure_response.get("results", []):
                    vid = batch_result.get("video_id")
                    for result in results:
                        if result.video_id == vid:
                            result.raw_responses["failure_mode"] = batch_result
                            result.failure_mode = self.parse_failure_mode(batch_result)
                            break
            except Exception as e:
                print(f"    ERROR in failure mode analysis: {e}")

        # Set SUCCESS for successful episodes
        for result in results:
            if result.overall_success is True:
                result.failure_mode = "SUCCESS"

        # Save results
        if output_file:
            self._save_results(results, output_file)

        return results

    def compute_metrics(self, results: list[EvaluationResult]) -> dict:
        """Compute aggregate metrics from evaluation results."""
        total = len(results)
        if total == 0:
            return {"error": "No results to compute metrics"}

        # Count successes (excluding None values)
        grasp_results = [r.grasp_success for r in results if r.grasp_success is not None]
        transport_results = [r.transport_success for r in results if r.transport_success is not None]
        place_results = [r.place_success for r in results if r.place_success is not None]
        overall_results = [r.overall_success for r in results if r.overall_success is not None]

        # Count failure modes
        failure_modes = {}
        for r in results:
            if r.failure_mode:
                failure_modes[r.failure_mode] = failure_modes.get(r.failure_mode, 0) + 1

        # Count errors
        errors = [r for r in results if r.error]

        metrics = {
            "total_episodes": total,
            "evaluated_episodes": total - len(errors),
            "errors": len(errors),
            "grasp_success_rate": sum(grasp_results) / len(grasp_results) if grasp_results else None,
            "grasp_evaluated": len(grasp_results),
            "transport_success_rate": sum(transport_results) / len(transport_results) if transport_results else None,
            "transport_evaluated": len(transport_results),
            "place_success_rate": sum(place_results) / len(place_results) if place_results else None,
            "place_evaluated": len(place_results),
            "overall_success_rate": sum(overall_results) / len(overall_results) if overall_results else None,
            "overall_evaluated": len(overall_results),
            "failure_modes": failure_modes,
        }

        return metrics

    def _save_results(self, results: list[EvaluationResult], output_file: str):
        """Save results to JSON file."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_episodes": len(results),
            "results": [asdict(r) for r in results],
            "metrics": self.compute_metrics(results),
        }
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def print_summary(self, results: list[EvaluationResult]):
        """Print a summary of evaluation results."""
        metrics = self.compute_metrics(results)

        print("\n" + "=" * 50)
        print("EVALUATION SUMMARY")
        print("=" * 50)
        print(f"Total Episodes: {metrics['total_episodes']}")
        print(f"Successfully Evaluated: {metrics['evaluated_episodes']}")
        print(f"Errors: {metrics['errors']}")
        print("-" * 50)

        if metrics["grasp_success_rate"] is not None:
            print(f"Grasp Success Rate: {metrics['grasp_success_rate']:.1%} ({metrics['grasp_evaluated']} episodes)")
        if metrics["transport_success_rate"] is not None:
            print(f"Transport Success Rate: {metrics['transport_success_rate']:.1%} ({metrics['transport_evaluated']} episodes)")
        if metrics["place_success_rate"] is not None:
            print(f"Place Success Rate: {metrics['place_success_rate']:.1%} ({metrics['place_evaluated']} episodes)")
        if metrics["overall_success_rate"] is not None:
            print(f"Overall Success Rate: {metrics['overall_success_rate']:.1%} ({metrics['overall_evaluated']} episodes)")

        if metrics["failure_modes"]:
            print("-" * 50)
            print("Failure Modes:")
            for mode, count in sorted(metrics["failure_modes"].items(), key=lambda x: -x[1]):
                print(f"  {mode}: {count}")

        print("=" * 50)


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-evaluate pick-and-place robotics episodes using NomadicML"
    )
    parser.add_argument(
        "--dataset",
        choices=["real", "sim"],
        default="real",
        help="Dataset to evaluate: 'real' (datasets/real_data/*.avi) or 'sim' (datasets/sim_data/*.mp4) (default: real)",
    )
    parser.add_argument(
        "--camera",
        choices=["front_cam", "workspace_cam"],
        default="front_cam",
        help="Camera view for sim dataset (default: front_cam)",
    )
    parser.add_argument(
        "video_dir",
        nargs="?",
        default=None,
        help="Directory containing video files (overrides --dataset)",
    )
    parser.add_argument(
        "--pattern",
        default=None,
        help="Glob pattern for video files (default: *.avi for real, *.mp4 for sim)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit number of videos to evaluate (default: 10 for testing)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="evaluation_results.json",
        help="Output JSON file for results (default: evaluation_results.json)",
    )
    parser.add_argument(
        "--api-key",
        help="NomadicML API key (or set NOMADICML_API_KEY env var)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use batch mode: upload all videos first, then analyze in batch (faster)",
    )
    parser.add_argument(
        "--folder",
        help="Folder name for organizing uploads in NomadicML (optional)",
    )
    parser.add_argument(
        "--use-folder",
        help="Use existing folder from NomadicML account (skip upload, just analyze)",
    )
    parser.add_argument(
        "--from-json",
        nargs="+",
        help="Load video IDs from JSON files (e.g., datasets/front_cam.json datasets/real_robot_data.json)",
    )

    args = parser.parse_args()

    # Determine video directory and pattern based on dataset choice
    if args.video_dir:
        video_dir = args.video_dir
        pattern = args.pattern or "*.avi"
    elif args.dataset == "real":
        video_dir = "datasets/real_data"
        pattern = args.pattern or "*.avi"
    else:  # sim
        video_dir = f"datasets/sim_data/observation.images.{args.camera}"
        pattern = args.pattern or "*.mp4"

    # Initialize evaluator
    evaluator = PickPlaceEvaluator(api_key=args.api_key)

    # Run evaluation
    if args.from_json:
        # Use video IDs from JSON files
        print(f"Loading video IDs from: {args.from_json}")
        print(f"Limit: {args.limit}")
        results = evaluator.evaluate_from_json(
            json_files=args.from_json,
            output_file=args.output,
            limit=args.limit,
        )
    elif args.use_folder:
        # Use existing folder from NomadicML
        print(f"Using existing NomadicML folder: {args.use_folder}")
        print(f"Limit: {args.limit}")
        results = evaluator.evaluate_from_folder(
            folder_name=args.use_folder,
            output_file=args.output,
            limit=args.limit,
        )
    else:
        # Upload and evaluate local videos
        print(f"Starting evaluation of videos in: {video_dir}")
        print(f"Pattern: {pattern}, Limit: {args.limit}, Batch mode: {args.batch}")
        results = evaluator.evaluate_dataset(
            video_dir=video_dir,
            pattern=pattern,
            limit=args.limit,
            output_file=args.output,
            batch_mode=args.batch,
            folder=args.folder,
        )

    # Print summary
    evaluator.print_summary(results)

    # Save final results
    evaluator._save_results(results, args.output)
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
