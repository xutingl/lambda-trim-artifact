import boto3
import sys
import argparse

from ltrimutil.aws import run_app_debloat


client = boto3.client("lambda")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run app debloat on AWS Lambda.")
    parser.add_argument("appname", type=str, help="Name of the application to debloat")
    parser.add_argument("-k", type=int, nargs='?', default=10, help="Number of iterations for debloat")
    parser.add_argument("--scoring", choices=['time', 'memory', 'cost', 'random'], default='cost', help="Scoring method for debloat")
    args = parser.parse_args()

    if len(sys.argv) < 2:
        print("Usage: python main.py <app_name>")
        sys.exit(1)

    result = run_app_debloat(client, args.appname, args.k, args.scoring, False)

    print(result)