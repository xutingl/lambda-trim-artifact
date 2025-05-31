import os
import boto3
import time
import argparse
import sys
parent_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parent_path)

from ltrimutil import get_aws_id, info, ok, warn, fail


def run_command(command: str):
    info(command)
    os.system(command)

def create_new_function(client, function_name: str, aws_id: str):
    try:
        response = client.delete_function(
            FunctionName=function_name,
        )
        info("Deleting function")
        time.sleep(30)
    except Exception as e:
        warn(f"Delete function error! It is fine if the function has never been created.\n{e}")

    try:
        
        response = client.create_function(
            FunctionName=function_name,
            PackageType="Image",
            Code={
                "ImageUri": f"{aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
            },
            Role=f"arn:aws:iam::{aws_id}:role/lambda-ex",
            Timeout=120,
            MemorySize=3008,
            EphemeralStorage={"Size": 5120},
            Architectures=["x86_64"],
        )
        info(f"Created function {function_name}.")
        time.sleep(120)
    except Exception as e:
        fail(f"Error when creating function! Remember to create it from image before invocation: {e}")

def create_baseline_function(repo_dir, client, app, image_name, function_name, aws_id, cleanup=False):
    info(f"Creating baseline function for app '{app}' with local image name '{image_name}' and AWS Lambda function name '{function_name}'.")
    if cleanup:
        run_command("sudo docker system prune -a -f") # Cleanup images to free up space
    run_command(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {aws_id}.dkr.ecr.us-east-1.amazonaws.com"
    )
    run_command(
        f"sudo docker build -f {repo_dir}/docker/baseline.Dockerfile -t {image_name} --build-arg APPNAME={app} {repo_dir}"
    )
    ok(f"Built baseline local image {image_name} for app {app}.")
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
    ok(f"Pushed image {image_name} to ECR repository {function_name}.")

    create_new_function(client, function_name, aws_id)
    ok(f"Successfully created baseline function for app '{app}' with local image name '{image_name}' and AWS Lambda function name '{function_name}'.")



if __name__ == "__main__":
    AWS_ID = get_aws_id()
    REPO_DIR = f"{os.path.dirname(__file__)}/.."

    # parse argument
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--app_name", type=str, required=True)
    parser.add_argument("-f", "--function_name", type=str, required=True)
    parser.add_argument("-s", "--snap_start", default=False, action="store_true")
    args = parser.parse_args()

    APP_NAME = args.app_name
    FUNCTION_NAME = args.function_name
    snap_start = args.snap_start

    client = boto3.client("lambda")

    if snap_start:
        info(f"Creating a SnapStart function '{FUNCTION_NAME}' using zip file {APP_NAME}")

        create_new_function(client, FUNCTION_NAME, AWS_ID, snap_start=True, zip_file=APP_NAME)

        info(f"Succeeded.")
        exit(0)

    IMAGE_NAME = f"{FUNCTION_NAME}:baseline"

    info(f"Creating the baseline for App name: '{APP_NAME}', function name: '{FUNCTION_NAME}'. Local image name: {IMAGE_NAME}")

    # # run_command("sudo docker system prune -a -f") # Cleanup images
    run_command(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {AWS_ID}.dkr.ecr.us-east-1.amazonaws.com"
    )



    run_command(
        f"sudo docker build -f {REPO_DIR}/baseline.Dockerfile -t {IMAGE_NAME} --build-arg APPNAME={APP_NAME} {REPO_DIR}"
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


    print(f"Baseline function image name: {IMAGE_NAME}. Uploaded function name: {FUNCTION_NAME}")


