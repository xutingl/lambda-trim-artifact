import time

start = time.time()
import subprocess

from lambda_criu import handler

# subprocess.run(["/var/task/criu/criu/criu", "service", "-d"])
subprocess.run(["/var/task/criu/criu/criu", "service", "-d", "--lazy-pages"])
end_import = time.time()

import_time = end_import - start
print(f"Import time: {import_time}")


def lambda_handler(event, context):
    handler(event, context)
    total = time.time() - start
    return {"import_time": import_time}


if __name__ == "__main__":
    print(lambda_handler({}, None))
