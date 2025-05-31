import time

start = time.time()
import subprocess


def handler(event, context):

    subprocess.run(
        [
            "/var/task/criu/criu/criu",
            "restore",
            "-D",
            "/var/task/checkpoint/",
            "--shell-job",
            "--lazy-pages",
            "-v4",
            "-o",
            "restore.log",
        ]
    )
    end = time.time()
    total = end - start

    import os

    DEBLOAT = os.getenv("DEBLOAT_ENV", "False")
    if DEBLOAT == "on":
        filename = "output/criu_debloated.txt"
    else:
        filename = "output/criu_normal.txt"

    with open(filename, "a") as f:
        f.write(f"{total}\n")
    return {"e2e": total}


if __name__ == "__main__":
    print(handler({}, None))
