import sys
import os
import argparse
import boto3
import pandas as pd
from pathlib import Path
parent_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parent_path)

from ltrimutil import info, ok, warn, fail, get_aws_id
from create_baseline import create_baseline_function
from debloat import create_debloat_function
from invoke import serial_invoke

all_apps = [
    "chdb-olap",
    "dna-visualization",
    "epub-pdf",
    "ffmpeg",
    "huggingface",
    "igraph",
    "image-resize",
    "jsym",
    "lightgbm",
    "lxml",
    "markdown",
    "pandas",
    "qiskit-nature",
    "resnet",
    "scikit",
    "shapely-numpy",
    "skimage",
    "spacy",
    "tensorflow", 
    "textblob",
    "wine"
]

if __name__ == "__main__":
    # Parse arguments: create-baseline, run-baseline, create-debloat, run-debloat
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--action", type=str, choices=["create-baseline", "run-baseline", "create-debloat", "run-debloat", "run-baseline-warm", "run-debloat-warm"], required=True,
        help="Action to perform: create or run baseline/debloat"
    )
    parser.add_argument(
        "-c", "--cleanup", action="store_true", default=False,
        help="Whether to clean up docker images to save space."
    )
    parser.add_argument(
        "--single-app", type=str, choices=all_apps, default=None,
    )
    args = parser.parse_args()
    action = args.action
    cleanup = args.cleanup

    OUTPUT_DIR = Path(os.path.dirname(__file__)) / "debloat" / "results"
    WARM_OUTPUT_DIR = Path(os.path.dirname(__file__)) / "warm" / "results"

    client = boto3.client("lambda")
    aws_id = get_aws_id()

    repo_dir = parent_path

    if args.single_app:
        all_apps = [args.single_app]
        info(f"Running action '{action}' for single app: {args.single_app}")

    if action == "create-baseline":
        info("Creating baseline functions for all apps")
        for app in all_apps:
            create_baseline_function(repo_dir, client, app, app, app, aws_id, cleanup=cleanup)
        ok("All baseline functions created successfully.")
    elif action == "run-baseline":
        info("Running baseline functions for all apps")
        baseline_output_dir = OUTPUT_DIR / "baseline"
        baseline_output_dir.mkdir(parents=True, exist_ok=True)
        for app in all_apps:
            function_name = app
            info(f"Invoking baseline function for {app} 100 times")
            import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst = serial_invoke(client, function_name, 100, warm_starts=False)

            df = pd.DataFrame({
                "e2e_latency": e2e_latencies,
                "mem_used": mem_used_lst,
                "duration": duration_lst,
                "billed_duration": billed_duration_lst,
                "import_time": import_times
            })
            df.to_csv(baseline_output_dir / f"{app}.csv", index=False)
            ok(f"Results for {app} saved to {baseline_output_dir / f'{app}.csv'}")
        ok("All baseline functions invoked successfully.")
    elif action == "create-debloat":
        info("Creating debloat functions for all apps")
        for app in all_apps:
            create_debloat_function(repo_dir, client, app, f"{app}:k20", f"{app}-k20", aws_id, k=20, cleanup=cleanup)
        ok("All debloat functions created successfully.")
    elif action == "run-debloat":
        info("Running debloated functions for all apps.")
        debloated_output_dir = OUTPUT_DIR / "debloated"
        debloated_output_dir.mkdir(parents=True, exist_ok=True)
        for app in all_apps:
            function_name = f"{app}-k20"
            info(f"Invoking debloated function '{function_name}' for {app} 100 times")
            import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst = serial_invoke(client, function_name, 100, warm_starts=False)
            df = pd.DataFrame({
                "e2e_latency": e2e_latencies,
                "mem_used": mem_used_lst,
                "duration": duration_lst,
                "billed_duration": billed_duration_lst,
                "import_time": import_times
            })
            df.to_csv(debloated_output_dir / f"{app}-debloat.csv", index=False)
            ok(f"Results for {app} saved to {debloated_output_dir / f'{app}-debloat.csv'}")
        ok("All debloated functions invoked successfully.")
    elif action == "run-baseline-warm":
        info("Running warm baseline functions for all apps")
        warm_baseline_output_dir = WARM_OUTPUT_DIR / "baseline_warm"
        warm_baseline_output_dir.mkdir(parents=True, exist_ok=True)
        for app in all_apps:
            function_name = app
            info(f"Invoking warm baseline function for {app} 100 times")
            import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst = serial_invoke(client, function_name, 100, warm_starts=True)

            df = pd.DataFrame({
                "e2e_latency": e2e_latencies,
                "mem_used": mem_used_lst,
                "duration": duration_lst,
                "billed_duration": billed_duration_lst,
                "import_time": import_times
            })
            df.to_csv(warm_baseline_output_dir / f"{app}.csv", index=False)
            ok(f"Results for {app} saved to {warm_baseline_output_dir / f'{app}.csv'}")
        ok("All warm baseline functions invoked successfully.")
    elif action == "run-debloat-warm":
        info("Running warm debloated functions for all apps.")
        warm_debloated_output_dir = WARM_OUTPUT_DIR / "debloated_warm"
        warm_debloated_output_dir.mkdir(parents=True, exist_ok=True)
        for app in all_apps:
            function_name = f"{app}-k20"
            info(f"Invoking warm debloated function '{function_name}' for {app} 100 times")
            import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst = serial_invoke(client, function_name, 100, warm_starts=True)
            df = pd.DataFrame({
                "e2e_latency": e2e_latencies,
                "mem_used": mem_used_lst,
                "duration": duration_lst,
                "billed_duration": billed_duration_lst,
                "import_time": import_times
            })
            df.to_csv(warm_debloated_output_dir / f"{app}-debloat.csv", index=False)
            ok(f"Results for {app} saved to {warm_debloated_output_dir / f'{app}-debloat.csv'}")
        ok("All warm debloated functions invoked successfully.")
    else:
        fail(f"Unknown action: {action}. Please choose from 'create-baseline', 'run-baseline', 'create-debloat', 'run-debloat', 'run-baseline-warm', or 'run-debloat-warm'.")

        

