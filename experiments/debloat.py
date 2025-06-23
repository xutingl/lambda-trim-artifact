import os
import boto3
import time
import argparse
import sys
parent_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parent_path)

from ltrimutil import get_aws_id, info, ok, warn, fail
from create_baseline import create_new_function

# This is required to debloat applications that use AWS services (i.e. boto3)
AWS_ACCESS_KEY_ID = "" # Insert your AWS Access Key ID here
AWS_SECRET_ACCESS_KEY = "" # Insert your AWS Secret Access Key here

def run_command(command: str):
    info(command)
    os.system(command)

def create_debloat_function(repo_dir, client, app, image_name, function_name, aws_id, k=10, with_fallback=False, cleanup=False, scoring="cost"):
    info(f"Creating debloat function for app '{app}' with local image name '{image_name}' and AWS Lambda function name '{function_name}'. k = {k}, scoring = {scoring}.")
    if cleanup:
        run_command("sudo docker system prune -a -f") # Cleanup images to free up space
    run_command(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {aws_id}.dkr.ecr.us-east-1.amazonaws.com"
    )
    run_command(
        f'sudo docker build -f {repo_dir}/docker/lambdatrim.Dockerfile -t {image_name} --build-arg APPNAME={app} --build-arg TOP_K={k} --build-arg SCORING={scoring} --build-arg WITH_FALLBACK="false" --build-arg AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID} --build-arg AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY} {repo_dir}'
    )
    ok(f"Built debloated local image {image_name} for app {app}.")

    run_command(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {aws_id}.dkr.ecr.us-east-1.amazonaws.com"
    )

    run_command(
        f"aws ecr create-repository --repository-name {function_name} --region us-east-1 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE"
    )
    run_command(
            f"sudo docker tag {image_name} {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
        )
    run_command(
        f"sudo docker push {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
    )
    create_new_function(client, function_name, aws_id)
    ok(f"Created debloated function {function_name} with image {image_name} for app {app}.")

def create_debloat_function_with_fallback(repo_dir, client, app, image_name, function_name, fallback_function_name, aws_id, k=10, cleanup=False, scoring="cost"):
    info(f"Creating debloat function for app '{app}' with local image name '{image_name}' and AWS Lambda function name '{function_name}'. Fallback function for it is '{fallback_function_name}'. k = {k}, scoring = {scoring}.")
    if cleanup:
        run_command("sudo docker system prune -a -f") # Cleanup images to free up space
    run_command(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {aws_id}.dkr.ecr.us-east-1.amazonaws.com"
    )
    run_command(
        f'sudo docker build -f {repo_dir}/docker/lambdatrim.Dockerfile -t {image_name} --build-arg APPNAME={app} --build-arg TOP_K={k} --build-arg SCORING={scoring} --build-arg WITH_FALLBACK="true" --build-arg FALLBACK_FUNCTION_NAME={fallback_function_name} --build-arg AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID} --build-arg AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY} {repo_dir}'
    )
    ok(f"Built debloated local image {image_name} for app {app}.")

    run_command(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {aws_id}.dkr.ecr.us-east-1.amazonaws.com"
    )

    run_command(
        f"aws ecr create-repository --repository-name {function_name} --region us-east-1 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE"
    )
    run_command(
            f"sudo docker tag {image_name} {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
        )
    run_command(
        f"sudo docker push {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
    )
    create_new_function(client, function_name, aws_id)
    ok(f"Created debloated function {function_name} with image {image_name} for app {app}.")


if __name__ == "__main__":
    AWS_ID = get_aws_id()
    REPO_DIR = f"{os.path.dirname(__file__)}/.."
    
    # parse argument
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--app_name", type=str, required=True)
    parser.add_argument("-k", "--debloat_k", type=int, default=10)
    parser.add_argument("--scoring", type=str, choices=['time', 'memory', 'cost', 'random'], default='cost')
    parser.add_argument("-w", "--with_fallback", action="store_true", default=False)
    parser.add_argument("-s", "--skip_original", action="store_true", default=False)
    args = parser.parse_args()

    APP_NAME = args.app_name
    k = args.debloat_k
    scoring = args.scoring
    with_fallback = args.with_fallback
    skip_original = args.skip_original

    info(f"Running debloater for App name: '{APP_NAME}'. k = {k}. with scoring = {scoring}. with_fallback = {with_fallback}. skip_original = {skip_original} (When true, it will ues the existing fallback function instead of creating a new one)")

    client = boto3.client("lambda")

    FUNCTION_NAME = f"{APP_NAME}-k{k}"
    IMAGE_NAME = f"{APP_NAME}:k{k}"

    FALLBACK_FUNCTION_NAME = f"{APP_NAME}"
    FALLBACK_IMAGE_NAME = f"{APP_NAME}:baseline"

    # # run_command("sudo docker system prune -a -f") # Cleanup images
    run_command(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {AWS_ID}.dkr.ecr.us-east-1.amazonaws.com"
    )

    if with_fallback:
        if skip_original:
            print(f'Skipping original function. There should be a fallback function named "{FALLBACK_FUNCTION_NAME}" already in AWS.')
        else:
            # Step 1: Build and push the fallback image (the original image without debloating)
            run_command(
                f"sudo docker build -f {REPO_DIR}/baseline.Dockerfile -t {FALLBACK_IMAGE_NAME} --build-arg APPNAME={APP_NAME} {REPO_DIR}"
            )
            run_command(
                f"aws ecr create-repository --repository-name {FALLBACK_FUNCTION_NAME} --region us-east-1 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE"
            )
            run_command(
                f"sudo docker tag {FALLBACK_IMAGE_NAME} {AWS_ID}.dkr.ecr.us-east-1.amazonaws.com/{FALLBACK_FUNCTION_NAME}:latest"
            )
            run_command(
                f"sudo docker push {AWS_ID}.dkr.ecr.us-east-1.amazonaws.com/{FALLBACK_FUNCTION_NAME}:latest"
            )
            print(f"Creating fallback function {FALLBACK_FUNCTION_NAME}")
            create_new_function(client, FALLBACK_FUNCTION_NAME, AWS_ID)
            print(f"Fallback image name: {FALLBACK_IMAGE_NAME}. Uploaded fallback function name: {FALLBACK_FUNCTION_NAME}")


    run_command(
        f"sudo docker build -f {REPO_DIR}/lambdatrim.Dockerfile -t {IMAGE_NAME} --build-arg APPNAME={APP_NAME} --build-arg SCORING={scoring} --build-arg TOP_K={k} --build-arg WITH_FALLBACK={with_fallback} {REPO_DIR}"
    )

    run_command(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {AWS_ID}.dkr.ecr.us-east-1.amazonaws.com"
    )

    run_command(
        f"aws ecr create-repository --repository-name {FUNCTION_NAME} --region us-east-1 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE"
    )
    run_command(
            f"sudo docker tag {IMAGE_NAME} {AWS_ID}.dkr.ecr.us-east-1.amazonaws.com/{FUNCTION_NAME}:latest"
        )
    run_command(
        f"sudo docker push {AWS_ID}.dkr.ecr.us-east-1.amazonaws.com/{FUNCTION_NAME}:latest"
    )

    create_new_function(client, FUNCTION_NAME, AWS_ID)


    print(f"Debloated image name: {IMAGE_NAME}. Uploaded function name: {FUNCTION_NAME}")


