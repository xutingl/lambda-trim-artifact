import functools


def checkpoint(func):
    """
    A decorator that creates a checkpoint using CRIU before executing the function.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        import time

        start = time.time()
        import os
        import socket

        import rpc_pb2 as rpc

        # Create a checkpoint directory
        checkpoint_dir = os.path.join(os.getcwd(), "checkpoint")
        os.makedirs(checkpoint_dir, exist_ok=True)

        # Connect to service socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        s.connect("./criu_service.socket")

        req = rpc.criu_req()
        req.type = rpc.DUMP
        req.opts.leave_running = True
        req.opts.log_level = 4
        req.opts.shell_job = True
        req.opts.images_dir_fd = os.open(checkpoint_dir, os.O_DIRECTORY)
        # Send request
        s.send(req.SerializeToString())

        # Recv response
        resp = rpc.criu_resp()
        MAX_MSG_SIZE = 1024
        resp.ParseFromString(s.recv(MAX_MSG_SIZE))

        end = time.time()
        print(f"Checkpointing took {end - start} seconds")

        # # Lazy-pages daemon
        import subprocess

        subprocess.run(
            ["/var/task/criu/criu/criu", "lazy-pages", "-D", checkpoint_dir, "-d"]
        )

        return
        # return func(*args, **kwargs)

    return wrapper
