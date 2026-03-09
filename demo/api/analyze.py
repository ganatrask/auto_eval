from http.server import BaseHTTPRequestHandler
import os
import json
import base64
import tempfile


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            from nomadicml import NomadicML
            from nomadicml.video import AnalysisType

            api_key = os.environ.get('NOMADICML_API_KEY')
            if not api_key:
                self._send_json({'error': 'NOMADICML_API_KEY not configured', 'success': False}, 500)
                return

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            video_base64 = data.get('video')
            video_filename = data.get('filename', 'video.mp4')
            queries = data.get('queries', [])

            if not video_base64:
                self._send_json({'error': 'No video data provided', 'success': False}, 400)
                return

            if not queries:
                self._send_json({'error': 'No queries provided', 'success': False}, 400)
                return

            video_data = base64.b64decode(video_base64)

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                tmp.write(video_data)
                video_path = tmp.name

            try:
                client = NomadicML(api_key=api_key)

                # Upload video - use the correct API format
                upload_result = client.upload(video_path)
                video_id = upload_result.get('video_id')

                if not video_id:
                    self._send_json({'error': 'Failed to upload video: ' + str(upload_result), 'success': False}, 500)
                    return

                # Run analyses for each query
                results = []
                for query in queries:
                    try:
                        # Use single video_id (not list) for analyze
                        analysis_result = client.analyze(
                            video_id,
                            analysis_type=AnalysisType.ASK,
                            custom_event=query
                        )

                        # Parse the response into clean, readable format
                        if analysis_result:
                            parsed = self._parse_analysis(analysis_result)
                            results.append({
                                'query': query,
                                'summary': parsed['summary'],
                                'events': parsed['events'],
                                'success': True
                            })
                        else:
                            results.append({
                                'query': query,
                                'summary': 'No response from analysis',
                                'events': [],
                                'success': False
                            })

                    except Exception as e:
                        results.append({'query': query, 'error': str(e), 'success': False})

                self._send_json({'success': True, 'video_id': video_id, 'results': results})

            finally:
                os.unlink(video_path)

        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON', 'success': False}, 400)
        except Exception as e:
            self._send_json({'error': str(e), 'success': False}, 500)

    def _parse_analysis(self, result):
        """Parse NomadML analysis result into clean format"""
        summary = ''
        events = []

        # Extract summary
        if 'summary' in result:
            summary = result['summary']
            # Clean up escape sequences
            summary = summary.replace('\\n', '\n').replace('\\\\n', '\n')
            # Remove the "Events found across the video:" prefix if present
            if summary.startswith('Events found across the video:'):
                summary = summary.replace('Events found across the video:', '').strip()

        # Extract events into readable format
        if 'events' in result and isinstance(result['events'], list):
            for event in result['events']:
                event_info = {
                    'time': f"{event.get('t_start', '?')} - {event.get('t_end', '?')}",
                    'label': event.get('label', 'Event'),
                    'description': event.get('aiAnalysis', ''),
                    'confidence': event.get('confidence', 0)
                }
                events.append(event_info)

        # If no summary but we have events, create one
        if not summary and events:
            summary = f"Found {len(events)} event(s) in the video."

        # Fallback to string representation
        if not summary:
            summary = str(result)

        return {'summary': summary, 'events': events}

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
