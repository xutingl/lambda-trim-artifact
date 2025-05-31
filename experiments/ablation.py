import sys
import os
import argparse
import boto3
import pandas as pd
from pathlib import Path
parent_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
print(parent_path)
sys.path.append(parent_path)

from ltrimutil import info, ok, warn, fail, get_aws_id
from create_baseline import create_baseline_function
from debloat import create_debloat_function
from invoke import serial_invoke

all_apps = [
    "dna-visualization",
    "lightgbm",
    "spacy"
]

OUTPUT_DIR = Path(os.path.dirname(__file__)) / "ablation" / "results"

if __name__ == "__main__":
    # Parse arguments: create-baseline, run-baseline, create-debloat, run-debloat
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--cleanup", action="store_true", default=False,
        help="Whether to clean up docker images to save space."
    )
    parser.add_argument(
        "--single-app", type=str, choices=all_apps, default=None,
    )
    parser.add_argument(
        "-k", type=int, default=20,
        help="Number of iterations for debloat (default: 20)"
    )
    parser.add_argument(
        "--scoring", choices=['time', 'memory', 'cost', 'random'], default='cost',
        help="Scoring method for debloat (default: cost)"
    )
    args = parser.parse_args()
    scoring = args.scoring
    k = args.k
    cleanup = args.cleanup

    client = boto3.client("lambda")
    aws_id = get_aws_id()

    repo_dir = parent_path

    if args.single_app:
        all_apps = [args.single_app]
        info(f"Running ablation for single app: {args.single_app}")

    info("Creating debloat functions for all apps")
    for app in all_apps:
        create_debloat_function(repo_dir, client, app, f"{app}:k{k}", f"{app}-k{k}", aws_id, k=k, with_fallback=False, cleanup=cleanup, scoring=scoring)
    ok("All debloat functions created successfully.")
    info("Running debloated functions for all apps.")
    debloated_output_dir = OUTPUT_DIR / "debloated"
    debloated_output_dir.mkdir(parents=True, exist_ok=True)
    for app in all_apps:
        function_name = f"{app}-k{k}"
        info(f"Invoking debloated function '{function_name}' for {app} 100 times")
        import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst = serial_invoke(client, function_name, 100, warm_starts=False)
        df = pd.DataFrame({
            "e2e_latency": e2e_latencies,
            "mem_used": mem_used_lst,
            "duration": duration_lst,
            "billed_duration": billed_duration_lst,
            "import_time": import_times
        })
        df.to_csv(debloated_output_dir / f"{app}_k{k}_{scoring}.csv", index=False)
        ok(f"Results for {app} saved to {debloated_output_dir / f'{app}_k{k}_{scoring}.csv'}")
    ok("All debloated functions invoked successfully.")
    
        

