#!/usr/bin/env python3
"""
Generate an HTML viewer for the analysis results with better visualization.
"""

import json
import webbrowser
from pathlib import Path
from collections import defaultdict

RESULTS_FILE = "simple_analysis_results.json"
OUTPUT_HTML = "results_viewer.html"


def load_results():
    with open(RESULTS_FILE) as f:
        return json.load(f)


def generate_html(data):
    results = data.get("response", {}).get("results", [])
    video_info = data.get("video_info", {})

    # Count stats by dataset
    dataset_stats = defaultdict(lambda: {"yes": 0, "no": 0})
    rows = []

    for r in results:
        vid = r.get("video_id", "")
        info = video_info.get(vid, {})
        title = info.get("title", "Unknown")
        dataset = info.get("dataset", "Unknown")

        events = r.get("events", [])
        if events:
            event = events[0]
            analysis = event.get("aiAnalysis", "")
            confidence = event.get("confidence", 0)
            t_start = event.get("t_start", "")
            t_end = event.get("t_end", "")
            label = event.get("label", "")
        else:
            analysis = r.get("summary", "No analysis")
            confidence = 0
            t_start = ""
            t_end = ""
            label = ""

        # Determine YES/NO
        is_yes = analysis.upper().startswith("YES")
        if is_yes:
            dataset_stats[dataset]["yes"] += 1
            status_class = "success"
            status_text = "SUCCESS"
            status_icon = "✓"
        else:
            dataset_stats[dataset]["no"] += 1
            status_class = "failure"
            status_text = "FAILED"
            status_icon = "✗"

        # Truncate analysis for display
        short_analysis = analysis[:200] + "..." if len(analysis) > 200 else analysis

        rows.append({
            "vid": vid,
            "title": title,
            "dataset": dataset,
            "status_class": status_class,
            "status_text": status_text,
            "status_icon": status_icon,
            "confidence": confidence,
            "t_start": t_start,
            "t_end": t_end,
            "label": label,
            "analysis": analysis,
            "short_analysis": short_analysis,
        })

    # Calculate totals
    total_yes = sum(d["yes"] for d in dataset_stats.values())
    total_no = sum(d["no"] for d in dataset_stats.values())
    total = total_yes + total_no
    success_rate = (total_yes / total * 100) if total > 0 else 0

    # Generate dataset chart data
    datasets = list(dataset_stats.keys())
    dataset_yes = [dataset_stats[d]["yes"] for d in datasets]
    dataset_no = [dataset_stats[d]["no"] for d in datasets]

    # Generate dataset pills HTML
    dataset_pills_html = '<button class="dataset-pill active" onclick="filterByDataset(\'all\')">All Datasets</button>'
    for d in datasets:
        count = dataset_stats[d]["yes"] + dataset_stats[d]["no"]
        dataset_pills_html += f'<button class="dataset-pill" onclick="filterByDataset(\'{d}\')">{d} ({count})</button>'

    # Generate rows HTML
    rows_html = ""
    for r in rows:
        rows_html += f"""
        <div class="card {r['status_class']}" data-dataset="{r['dataset']}" data-status="{r['status_class']}">
            <div class="card-header">
                <div class="status-badge {r['status_class']}">
                    <span class="status-icon">{r['status_icon']}</span>
                    {r['status_text']}
                </div>
                <div class="confidence-meter">
                    <div class="confidence-fill" style="width: {r['confidence']*100:.0f}%"></div>
                    <span class="confidence-text">{r['confidence']:.0%}</span>
                </div>
            </div>
            <div class="card-body">
                <div class="card-title">{r['title']}</div>
                <div class="card-meta">
                    <span class="dataset-tag">{r['dataset']}</span>
                    <span class="time-tag">{r['t_start']} - {r['t_end']}</span>
                </div>
                <div class="card-label">{r['label']}</div>
                <div class="card-analysis">{r['short_analysis']}</div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robot Pick & Place Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
        }}
        header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #4ade80, #60a5fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #888;
            font-size: 1rem;
        }}

        /* Stats Section */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 25px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }}
        .stat-icon {{
            font-size: 2rem;
            margin-bottom: 10px;
        }}
        .stat-card.success .stat-icon {{ color: #4ade80; }}
        .stat-card.failure .stat-icon {{ color: #f87171; }}
        .stat-card.total .stat-icon {{ color: #60a5fa; }}
        .stat-card.rate .stat-icon {{ color: #fbbf24; }}
        .stat-number {{
            font-size: 3rem;
            font-weight: 800;
            line-height: 1;
        }}
        .stat-card.success .stat-number {{ color: #4ade80; }}
        .stat-card.failure .stat-number {{ color: #f87171; }}
        .stat-card.total .stat-number {{ color: #60a5fa; }}
        .stat-card.rate .stat-number {{ color: #fbbf24; }}
        .stat-label {{
            color: #888;
            font-size: 0.9rem;
            margin-top: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* Charts Section */
        .charts-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }}
        @media (max-width: 900px) {{
            .charts-section {{
                grid-template-columns: 1fr;
            }}
        }}
        .chart-container {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .chart-title {{
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #fff;
        }}
        .chart-wrapper {{
            position: relative;
            height: 250px;
        }}

        /* Filters */
        .filters {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            padding: 12px 28px;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.3s;
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 2px solid transparent;
        }}
        .filter-btn:hover {{
            background: rgba(255,255,255,0.2);
        }}
        .filter-btn.active {{
            border-color: #fff;
        }}
        .filter-btn.all.active {{ background: #60a5fa; color: #000; }}
        .filter-btn.yes.active {{ background: #4ade80; color: #000; }}
        .filter-btn.no.active {{ background: #f87171; color: #000; }}

        /* Search */
        .search-container {{
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
        }}
        .search-box {{
            position: relative;
            width: 100%;
            max-width: 500px;
        }}
        .search-box input {{
            width: 100%;
            padding: 15px 25px 15px 50px;
            border-radius: 50px;
            border: 2px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 1rem;
            transition: all 0.3s;
        }}
        .search-box input:focus {{
            outline: none;
            border-color: #60a5fa;
            background: rgba(255,255,255,0.1);
        }}
        .search-box input::placeholder {{
            color: #666;
        }}
        .search-icon {{
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: #666;
        }}

        /* Results Grid */
        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
        }}
        .card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.3);
        }}
        .card.success {{
            border-left: 4px solid #4ade80;
        }}
        .card.failure {{
            border-left: 4px solid #f87171;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: rgba(0,0,0,0.2);
        }}
        .status-badge {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .status-badge.success {{
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
        }}
        .status-badge.failure {{
            background: rgba(248, 113, 113, 0.2);
            color: #f87171;
        }}
        .status-icon {{
            font-size: 1rem;
        }}
        .confidence-meter {{
            position: relative;
            width: 80px;
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }}
        .confidence-fill {{
            height: 100%;
            background: linear-gradient(90deg, #fbbf24, #4ade80);
            border-radius: 4px;
        }}
        .confidence-text {{
            position: absolute;
            right: -45px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.75rem;
            color: #888;
        }}
        .card-body {{
            padding: 20px;
        }}
        .card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 10px;
            color: #fff;
        }}
        .card-meta {{
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
        }}
        .dataset-tag, .time-tag {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            background: rgba(96, 165, 250, 0.2);
            color: #60a5fa;
        }}
        .time-tag {{
            background: rgba(168, 85, 247, 0.2);
            color: #a855f7;
        }}
        .card-label {{
            font-size: 0.9rem;
            color: #fbbf24;
            margin-bottom: 10px;
            font-weight: 500;
        }}
        .card-analysis {{
            font-size: 0.85rem;
            color: #999;
            line-height: 1.5;
        }}
        .hidden {{
            display: none !important;
        }}

        /* Dataset Filter Pills */
        .dataset-filters {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .dataset-pill {{
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            cursor: pointer;
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: none;
            transition: all 0.3s;
        }}
        .dataset-pill:hover {{
            background: rgba(255,255,255,0.2);
        }}
        .dataset-pill.active {{
            background: #a855f7;
            color: #fff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Robot Pick & Place Analysis</h1>
            <p class="subtitle">Automated evaluation results from {total} video clips</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card success">
                <div class="stat-icon">✓</div>
                <div class="stat-number">{total_yes}</div>
                <div class="stat-label">Successful</div>
            </div>
            <div class="stat-card failure">
                <div class="stat-icon">✗</div>
                <div class="stat-number">{total_no}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card total">
                <div class="stat-icon">▶</div>
                <div class="stat-number">{total}</div>
                <div class="stat-label">Total Videos</div>
            </div>
            <div class="stat-card rate">
                <div class="stat-icon">%</div>
                <div class="stat-number">{success_rate:.1f}</div>
                <div class="stat-label">Success Rate</div>
            </div>
        </div>

        <div class="charts-section">
            <div class="chart-container">
                <div class="chart-title">Overall Results</div>
                <div class="chart-wrapper">
                    <canvas id="donutChart"></canvas>
                </div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Results by Dataset</div>
                <div class="chart-wrapper">
                    <canvas id="barChart"></canvas>
                </div>
            </div>
        </div>

        <div class="filters">
            <button class="filter-btn all active" onclick="filterByStatus('all')">All ({total})</button>
            <button class="filter-btn yes" onclick="filterByStatus('success')">Success ({total_yes})</button>
            <button class="filter-btn no" onclick="filterByStatus('failure')">Failed ({total_no})</button>
        </div>

        <div class="dataset-filters">
            {dataset_pills_html}
        </div>

        <div class="search-container">
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="search" placeholder="Search by video title..." oninput="searchResults()">
            </div>
        </div>

        <div class="results-grid" id="results-grid">
            {rows_html}
        </div>
    </div>

    <script>
        // Charts
        const donutCtx = document.getElementById('donutChart').getContext('2d');
        new Chart(donutCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Success', 'Failed'],
                datasets: [{{
                    data: [{total_yes}, {total_no}],
                    backgroundColor: ['#4ade80', '#f87171'],
                    borderWidth: 0,
                    hoverOffset: 10
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: '#fff', padding: 20, font: {{ size: 14 }} }}
                    }}
                }}
            }}
        }});

        const barCtx = document.getElementById('barChart').getContext('2d');
        new Chart(barCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(datasets)},
                datasets: [
                    {{
                        label: 'Success',
                        data: {json.dumps(dataset_yes)},
                        backgroundColor: '#4ade80',
                        borderRadius: 8
                    }},
                    {{
                        label: 'Failed',
                        data: {json.dumps(dataset_no)},
                        backgroundColor: '#f87171',
                        borderRadius: 8
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        stacked: true,
                        grid: {{ display: false }},
                        ticks: {{ color: '#888' }}
                    }},
                    y: {{
                        stacked: true,
                        grid: {{ color: 'rgba(255,255,255,0.1)' }},
                        ticks: {{ color: '#888' }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: '#fff', padding: 20, font: {{ size: 14 }} }}
                    }}
                }}
            }}
        }});

        // Filtering
        let currentStatus = 'all';
        let currentDataset = 'all';

        function filterByStatus(status) {{
            currentStatus = status;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            applyFilters();
        }}

        function filterByDataset(dataset) {{
            currentDataset = dataset;
            document.querySelectorAll('.dataset-pill').forEach(pill => pill.classList.remove('active'));
            event.target.classList.add('active');
            applyFilters();
        }}

        function searchResults() {{
            applyFilters();
        }}

        function applyFilters() {{
            const searchTerm = document.getElementById('search').value.toLowerCase();
            const cards = document.querySelectorAll('.card');

            cards.forEach(card => {{
                const matchesStatus = currentStatus === 'all' || card.dataset.status === currentStatus;
                const matchesDataset = currentDataset === 'all' || card.dataset.dataset === currentDataset;
                const text = card.textContent.toLowerCase();
                const matchesSearch = text.includes(searchTerm);

                card.classList.toggle('hidden', !(matchesStatus && matchesDataset && matchesSearch));
            }});
        }}
    </script>
</body>
</html>
"""
    return html


def main():
    print("Loading results...")
    data = load_results()

    print("Generating HTML...")
    html = generate_html(data)

    print(f"Saving to {OUTPUT_HTML}...")
    with open(OUTPUT_HTML, "w") as f:
        f.write(html)

    print(f"Opening in browser...")
    webbrowser.open(f"file://{Path(OUTPUT_HTML).absolute()}")
    print("Done!")


if __name__ == "__main__":
    main()
