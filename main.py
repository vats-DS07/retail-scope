"""
main.py - runs the whole project pipeline in order.

    python main.py            # clean the data, run the EDA, build all charts
    python main.py --serve    # same, then open the website at http://localhost:8000

Step 1: analysis/data_cleaning.py       -> dataset/cleaned_dataset.csv(.gz) + reports/
Step 2: analysis/exploratory_analysis.py -> visualizations/*.png + static/data.js

Only the Python standard library is used here.
"""

import http.server
import functools
import runpy
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_step(title, script):
    print("\n" + "#" * 70)
    print(f"# {title}")
    print("#" * 70)
    start = time.time()
    runpy.run_path(str(ROOT / "analysis" / script), run_name="__main__")
    print(f"-> finished in {time.time() - start:.1f} s")


def serve(port=8000):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    url = f"http://localhost:{port}/"
    print(f"\nServing the website at {url}  (press Ctrl+C to stop)")
    webbrowser.open(url)
    with http.server.ThreadingHTTPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    if "--serve-only" not in sys.argv:
        run_step("STEP 1 - DATA CLEANING", "data_cleaning.py")
        run_step("STEP 2 - EXPLORATORY DATA ANALYSIS AND CHARTS", "exploratory_analysis.py")
        print("\nAll done. Open index.html in a browser, or run:  python main.py --serve-only")
    if "--serve" in sys.argv or "--serve-only" in sys.argv:
        serve()
