from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import os
import json


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        try:
            from nomadicml import NomadicML

            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            batch_id = params.get('batch_id', [None])[0]

            if not batch_id:
                self._send_json({'error': 'batch_id required', 'success': False}, 400)
                return

            api_key = os.environ.get('NOMADICML_API_KEY')
            if not api_key:
                self._send_json({'error': 'NOMADICML_API_KEY not configured', 'success': False}, 500)
                return

            client = NomadicML(api_key=api_key)

            try:
                batch_results = client.get_batch_analysis(batch_id=batch_id)
                if batch_results:
                    result_data = batch_results[0] if isinstance(batch_results, list) else batch_results
                    self._send_json({
                        'success': True,
                        'status': 'completed',
                        'result': {
                            'response': result_data.get('response', str(result_data)),
                            'confidence': result_data.get('confidence', 'N/A')
                        }
                    })
                else:
                    self._send_json({'success': True, 'status': 'pending'})
            except:
                self._send_json({'success': True, 'status': 'pending'})

        except Exception as e:
            self._send_json({'error': str(e), 'success': False}, 500)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
