import sys
import os
import argparse
import boto3
import pandas as pd
from pathlib import Path
parent_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parent_path)

from ltrimutil import info, ok, warn, fail, get_aws_id
from debloat import create_debloat_function_with_fallback
from invoke import serial_invoke_with_fallback

all_apps = [
    "dna-visualization",
    "huggingface",
    "lightgbm",
    "spacy",
]

def invoke_function_with_fallback(client, function_name, fallback_function_name, principal_warm, fallback_warm, output_dir, repeat=100):
    info(f"Invoking debloated function '{function_name}' for {app} {repeat} times.")
    import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst = serial_invoke_with_fallback(client, function_name, fallback_function_name, repeat, principal_warm, fallback_warm)
    df = pd.DataFrame({
        "e2e_latency": e2e_latencies,
        "mem_used": mem_used_lst,
        "duration": duration_lst,
        "billed_duration": billed_duration_lst,
        "import_time": import_times
    })
    filename = output_dir / f"{function_name}.csv"
    df.to_csv(filename, index=False)
    ok(f"Results for {function_name} saved to {filename}")


if __name__ == "__main__":
    # Parse arguments: create-baseline, run-baseline, create-debloat, run-debloat
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--action", type=str, choices=["create-debloat-with-fallback", "run-cold-cold", "run-cold-warm", "run-warm-cold", "run-warm-warm"], required=True,
        help="Action to perform"
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

    OUTPUT_DIR = Path(os.path.dirname(__file__)) / "fallback" / "results"

    client = boto3.client("lambda")
    aws_id = get_aws_id()

    repo_dir = parent_path

    if args.single_app:
        all_apps = [args.single_app]
        info(f"Running action '{action}' for single app: {args.single_app}")

    if action == "create-debloat-with-fallback":
        info("Creating debloat functions for all apps with fallback.")
        for app in all_apps:
            fallback_function_name = app
            create_debloat_function_with_fallback(repo_dir, client, app, f"{app}:fallback", f"{app}-with-fallback", fallback_function_name, aws_id, k=1, cleanup=cleanup)
        ok("All debloat functions with fallback created successfully.")
    elif action == "run-cold-cold":
        info("Invoking function with principal function cold and fallback function cold.")
        output_dir = OUTPUT_DIR / "cold_cold"
        output_dir.mkdir(parents=True, exist_ok=True)
        for app in all_apps:
            function_name = f"{app}-with-fallback"
            fallback_function_name = app
            invoke_function_with_fallback(client, function_name, fallback_function_name, principal_warm=False, fallback_warm=False, output_dir=output_dir)
        ok("All debloated functions invoked successfully. Principal: cold, Fallback: cold.")
    elif action == "run-cold-warm":
        info("Invoking function with principal function cold and fallback function warm.")
        output_dir = OUTPUT_DIR / "cold_warm"
        output_dir.mkdir(parents=True, exist_ok=True)
        for app in all_apps:
            function_name = f"{app}-with-fallback"
            fallback_function_name = app
            invoke_function_with_fallback(client, function_name, fallback_function_name, principal_warm=False, fallback_warm=True, output_dir=output_dir)
        ok("All debloated functions invoked successfully. Principal: cold, Fallback: warm.")
    elif action == "run-warm-cold":
        info("Invoking function with principal function warm and fallback function cold.")
        output_dir = OUTPUT_DIR / "warm_cold"
        output_dir.mkdir(parents=True, exist_ok=True)
        for app in all_apps:
            function_name = f"{app}-with-fallback"
            fallback_function_name = app
            invoke_function_with_fallback(client, function_name, fallback_function_name, principal_warm=True, fallback_warm=False, output_dir=output_dir)
        ok("All debloated functions invoked successfully. Principal: warm, Fallback: cold.")
    elif action == "run-warm-warm":
        info("Invoking function with principal function warm and fallback function warm.")
        output_dir = OUTPUT_DIR / "warm_warm"
        output_dir.mkdir(parents=True, exist_ok=True)
        for app in all_apps:
            function_name = f"{app}-with-fallback"
            fallback_function_name = app
            invoke_function_with_fallback(client, function_name, fallback_function_name, principal_warm=True, fallback_warm=True, output_dir=output_dir)
        ok("All debloated functions invoked successfully. Principal: warm, Fallback: warm.")
    else:
        fail(f"Unknown action: {action}.")

        

