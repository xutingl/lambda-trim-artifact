from original_lambda_function import handler as original_handler

def handler(event, context):
    try:
        return original_handler(event, context)
    except Exception as e:
        import boto3
        import json
        import os
        FALLBACK_FUNCTION_NAME = os.environ.get("FALLBACK_FUNCTION_NAME")
        client = boto3.client("lambda")

        print(f"Error detected, invoking fallback function: {FALLBACK_FUNCTION_NAME}")
        print(f"Error:")
        print(e)
        response = client.invoke(
            FunctionName=FALLBACK_FUNCTION_NAME,
            InvocationType="RequestResponse",
            LogType="Tail",
            Payload=json.dumps({}),
        )
        response_payload = json.load(response["Payload"])
        return response_payload        
