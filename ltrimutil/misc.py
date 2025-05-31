from termcolor import colored
from os import getcwd
from pathlib import Path


def info(info: str):
    print(f"{colored('info', color='blue')} {info}")


def ok(info: str):
    print(f"{colored('  ok', color='green')} {info}")


def fail(info: str):
    print(f"{colored('fail', color='red')} {info}")


def warn(info: str):
    print(f"{colored('warn', color='yellow')} {info}")

def collect_apps():
    cwd = getcwd()
    folder = Path(cwd + "/serverless-bench/examples")
    return [dir for dir in folder.iterdir() if dir.is_dir()]