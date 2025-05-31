import base64
import json
import subprocess

from time import sleep, time
from os import system, getcwd
from sys import exit

from ltrimutil.misc import *


def get_aws_id():
    info("fetching aws id")
    try:
        output = subprocess.check_output(
            ["aws", "sts", "get-caller-identity", "--output", "json"]
        ).decode()
        id: str = json.loads(output)["Account"]
        ok(f"fetched aws id = {id}")
        return id
    except Exception:
        warn("unable to get aws id, try to configure")
        system("aws configure")
        try:
            output = subprocess.check_output(
                ["aws", "sts", "get-caller-identity", "--output", "json"]
            ).decode()
            id: str = json.loads(output)["Account"]
            ok(f"fetched aws id = {id}")
            return id
        except Exception:
            fail("failed to get aws id, please check your account or setting")
            exit(1)


def create_lambda_function(
    client,
    function_name: str,
    aws_id: str,
):
    try:
        response = client.delete_function(
            FunctionName=function_name,
        )
        info("try deleting function")
        for _ in range(30 // 5):
            print(".", end="", flush=True)
            sleep(5)
        print("")
    except:
        warn("failed to delete function.")
        info("it is fine if the function has never been created.")

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
        info(f"try creating function {function_name}")
        for _ in range(180 // 5):
            print(".", end="", flush=True)
            sleep(5)
        ok(f"function {function_name} create successful")
    except:
        fail("failed to create function.")


def invoke_function(client, function_name: str, payload={}):
    latency_start = time()

    info(f"try invoking function {function_name}")
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        LogType="Tail",
        Payload=json.dumps(payload),
    )

    e2e_latency = time() - latency_start
    info(f"response received for function {function_name}")

    log_result = (base64.b64decode(response["LogResult"])).decode("utf-8")

    is_coldstart = False

    for line in log_result.split("\t"):
        if "Max Memory Used" in line:
            mem_used = line.split(" ")[-2]
        elif "Billed Duration" in line:
            billed_duration = line.split(" ")[-2]
        elif "Init Duration" in line:
            is_coldstart = True
        elif "Duration" in line and "Billed" not in line and "Init" not in line:
            duration = line.split(" ")[-2]

    response_payload = json.load(response["Payload"])
    if "import_time" not in response_payload:
        fail(f"invoking {function_name} failed!")
    import_time = response_payload["import_time"]

    result = (
        response,
        is_coldstart,
        *map(
            float,
            (
                mem_used,  # type: ignore
                import_time,
                billed_duration,  # type: ignore
                duration,  # type: ignore
                e2e_latency,
            ),
        ),
    )

    ok(f"total benchmark received for {function_name}, {result}")

    return result


def run_app_baseline(client, app_name: str, payload={}):
    aws_id = get_aws_id()
    image_name = f"{app_name}:baseline"
    function_name = f"{app_name}-baseline"

    info(f"building baseline docker image {image_name} for {app_name}")

    info("login docker with aws")
    system(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {aws_id}.dkr.ecr.us-east-1.amazonaws.com"
    )

    # build docker, at docker/baseline.Dockerfile
    info(f"build docker image {image_name}")
    cwd = getcwd()
    system(
        f"sudo docker build -f {cwd}/docker/baseline.Dockerfile -t {image_name} --build-arg APPNAME={app_name} {cwd}"
    )

    info(f"upload docker image {image_name} to aws")
    system(
        f"aws ecr create-repository --repository-name {function_name} --region us-east-1 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE"
    )
    system(
        f"sudo docker tag {image_name} {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
    )
    system(
        f"sudo docker push {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
    )

    ok(
        f"finished building and uploading {app_name} baseline image {image_name}, uploaded as function {function_name}"
    )

    create_lambda_function(client, function_name, aws_id)
    return invoke_function(client, function_name, payload)


def run_app_debloat(
    client,
    app_name: str,
    k: int,
    scoring: str,
    with_fallback: bool,
    skip_original: bool = False,
    payload={},
):
    aws_id = get_aws_id()
    image_name = f"{app_name}:debloat"
    fallback_image_name = f"{app_name}:fallback"
    function_name = f"{app_name}-debloat"
    fallback_function_name = f"{app_name}-fallback"
    cwd = getcwd()

    info(f"building baseline docker image {image_name} for {app_name}")

    info("login docker with aws")

    system(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {aws_id}.dkr.ecr.us-east-1.amazonaws.com"
    )

    if with_fallback:
        if skip_original:
            info("skipping original function.")
            info(
                f'fallback function "{fallback_function_name}" should be already uploaded in AWS.'
            )
        else:
            info(f"creating fallback function {function_name}")
            system(
                f"sudo docker build -f {cwd}/docker/baseline.Dockerfile -t {fallback_image_name} --build-arg APPNAME={app_name} {cwd}"
            )
            system(
                f"aws ecr create-repository --repository-name {fallback_function_name} --region us-east-1 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE"
            )
            system(
                f"sudo docker tag {fallback_image_name} {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{fallback_function_name}:latest"
            )
            system(
                f"sudo docker push {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{fallback_function_name}:latest"
            )
            info(f"creating fallback function {fallback_function_name}")
            create_lambda_function(client, fallback_function_name, aws_id)
            ok(f"fallback image {fallback_image_name} created")
            ok(f"fallback function {fallback_function_name} created")

    info(f"build docker image {image_name}")
    system(
        f"sudo docker build -f {cwd}/docker/lambdatrim.Dockerfile -t {image_name} --build-arg APPNAME={app_name} --build-arg TOP_K={k} --build-arg SCORING={scoring} --build-arg WITH_FALLBACK={with_fallback} {cwd}"
    )

    system(
        f"aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {aws_id}.dkr.ecr.us-east-1.amazonaws.com"
    )

    system(
        f"aws ecr create-repository --repository-name {function_name} --region us-east-1 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE"
    )
    system(
        f"sudo docker tag {image_name} {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
    )
    system(
        f"sudo docker push {aws_id}.dkr.ecr.us-east-1.amazonaws.com/{function_name}:latest"
    )
    ok(
        f"finished building and uploading {app_name} debloat image {image_name}, uploaded as function {function_name}"
    )
    create_lambda_function(client, function_name, aws_id)
    return invoke_function(client, function_name, payload)
