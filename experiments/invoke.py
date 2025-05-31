import os
import boto3
import time
import json
import pandas as pd
import base64
import argparse
import sys
parent_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parent_path)

from ltrimutil import info, ok, warn, fail, get_aws_id

import concurrent.futures
import threading

REPO_DIR = f"{os.path.dirname(__file__)}/.."


def run_command(command: str):
    info(command)
    os.system(command)

"""
Input:
    client: boto3.client("lambda")
    function_name: str. Name of the function on Lambda.
Output:
    Statistics of the invocation.
"""
def invoke_function(client, function_name: str, payload: dict = {}):
    latency_start = time.time()
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        LogType="Tail",
        Payload=json.dumps(payload),
    )
    e2e_latency = time.time() - latency_start

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
        fail("Invocation failed!")
        return response_payload
    import_time = response_payload["import_time"]

    return response, is_coldstart, mem_used, import_time, billed_duration, duration, e2e_latency

def parallel_invoke(client, function_name: str, num_invocations: int, warm_starts: bool = False, num_executor: int = 40):
    import_times = []
    e2e_latencies = []
    mem_used_lst = []
    duration_lst = []
    billed_duration_lst = []

    list_lock = threading.Lock()  # Lock to ensure thread-safe list updates

    def thread_safe_append(result, warm_starts: bool = False):
        if result:
            response, is_coldstart, mem_used, import_time, billed_duration, duration, e2e_latency = result

            if warm_starts == is_coldstart:
                warn(f"Failed invocation. We want to {'warm start' if warm_starts else 'cold start'} but it is {'cold start' if is_coldstart else 'warm start'}. This invocation's result will be discarded.")
                return

            with list_lock:
                import_times.append(import_time)
                e2e_latencies.append(e2e_latency)
                mem_used_lst.append(mem_used)
                duration_lst.append(duration)
                billed_duration_lst.append(billed_duration)

    for _ in range(num_invocations):
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_invocations) as executor:
            futures = [executor.submit(invoke_function, client, function_name) for _ in range(num_executor)]
            
            for future in concurrent.futures.as_completed(futures):
                thread_safe_append(future.result(), warm_starts=warm_starts)
    
    info(f"Invoked {num_invocations} * {num_executor} times. Number of accepted runs: {len(e2e_latencies)}.")
    info(f"Average e2e latency: {sum(e2e_latencies) / len(e2e_latencies)}")

    return import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst

def serial_invoke(client, function_name: str, repeat: int, warm_starts: bool = False):
    import_times = []
    e2e_latencies = []
    mem_used_lst = []
    duration_lst = []
    billed_duration_lst = []

    for i in range(repeat):

        if i % 5 == 0:
            info(f"repeating {i + 1}th time")
        
        if warm_starts:
            time.sleep(5)
        
        else:
            try:
                response = client.update_function_configuration(
                    FunctionName=function_name,
                    Description=f"run{i}",
                    Environment={
                        'Variables': {
                            'EXPERIMENT_RUN': f'run{i}'
                        }
                    },
                )
                time.sleep(10)
            except:
                time.sleep(10)
                continue

        results = invoke_function(client, function_name)
        if len(results) != 7:
            warn(f"Failed invocation at {i}th iteration. Response: {results}. This invocation's result will be discarded.")
            continue
        response, is_coldstart, mem_used, import_time, billed_duration, duration, e2e_latency = results

        if warm_starts == is_coldstart:
            warn(f"Incorrect invocation at {i}th iteration. We want to {'warm start' if warm_starts else 'cold start'} but it is {'cold start' if is_coldstart else 'warm start'}. This invocation's result will be discarded.")
            continue

        e2e_latencies.append(e2e_latency)
        mem_used_lst.append(mem_used)
        duration_lst.append(duration)
        billed_duration_lst.append(billed_duration)
        import_times.append(import_time)
    
    return import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst


def serial_invoke_with_fallback(client, function_name: str, fallback_function_name, repeat: int, principal_warm: bool = False, fallback_warm: bool = False):
    import_times = []
    e2e_latencies = []
    mem_used_lst = []
    duration_lst = []
    billed_duration_lst = []

    for i in range(repeat):

        if i % 5 == 0:
            info(f"repeating {i + 1}th time")
        
        if principal_warm:
            time.sleep(5)
        else:
            try:
                response = client.update_function_configuration(
                    FunctionName=function_name,
                    Description=f"run{i}",
                    Environment={
                        'Variables': {
                            'EXPERIMENT_RUN': f'run{i}'
                        }
                    },
                )
                time.sleep(10)
            except Exception as e:
                warn(f"Failed to update function at run{i} with exception {e}. Retrying.")
                continue
        
        if not fallback_warm:
            try:
                response = client.update_function_configuration(
                    FunctionName=fallback_function_name,
                    Description=f"run{i}",
                    Environment={
                        'Variables': {
                            'EXPERIMENT_RUN': f'run{i}'
                        }
                    },
                )
                time.sleep(10)
            except Exception as e:
                warn(f"Failed to update fallback function at run{i} with exception {e}. Retrying.")
                continue

        results = invoke_function(client, function_name, payload={"raise_exception": "1"}) # This payload is used to make the principal function raise an exception in order to trigger fallback.
        if len(results) != 7:
            fail(f"Failed invocation at {i}th iteration. Response: {results}")
            continue
        response, is_coldstart, mem_used, import_time, billed_duration, duration, e2e_latency = results

        if principal_warm == is_coldstart:
            warn(f"Incorrect invocation at {i}th iteration. We want to {'warm start' if principal_warm else 'cold start'} but it is {'cold start' if is_coldstart else 'warm start'}. This invocation's result will be discarded.")
            continue

        e2e_latencies.append(e2e_latency)
        mem_used_lst.append(mem_used)
        duration_lst.append(duration)
        billed_duration_lst.append(billed_duration)
        import_times.append(import_time)
    
    return import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst

    

if __name__ == "__main__":
    # parse argument
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--function_name", type=str, required=True)
    parser.add_argument("-r", "--repeat", type=int, default=1)
    parser.add_argument("-w", "--warm_start", action="store_true", default=False)
    parser.add_argument("-o", "--output_dir", type=str, default="./results/")
    parser.add_argument("-p", "--parallel", action="store_true", default=False, help="Invoke lambda in parallel. A different way to get cold start.")
    args = parser.parse_args()

    FUNCTION_NAME = args.function_name
    repeat = args.repeat
    warm_starts = args.warm_start
    output_dir = args.output_dir
    parallel = args.parallel

    info(f"Invoking function '{FUNCTION_NAME}', repeating {repeat} times. warm_starts: {warm_starts}. parallel invocation: {parallel}")

    client = boto3.client("lambda")

    if parallel:
        import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst = parallel_invoke(client, FUNCTION_NAME, repeat, warm_starts)
    else:
        import_times, e2e_latencies, mem_used_lst, duration_lst, billed_duration_lst = serial_invoke(client, FUNCTION_NAME, repeat, warm_starts)

    df = pd.DataFrame(
            {
                "e2e_latency": e2e_latencies,
                "mem_used": mem_used_lst,
                "duration": duration_lst,
                "billed_duration": billed_duration_lst,
                "import_time": import_times,
            }
        )

    df.to_csv(f"{output_dir}/{FUNCTION_NAME}.csv", index=False)
    print(f"Results saved to {output_dir}/{FUNCTION_NAME}.csv")

