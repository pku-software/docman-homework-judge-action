import abc
import json
import os
from typing import Callable, List

from termcolor import colored

from docman_judge.judge import JudgeResult


class ILogger(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def exec_func(self, func: Callable[[str], JudgeResult], ws_path: str) -> bool:
        pass

    @abc.abstractmethod
    def end(self) -> None:
        pass


def wrap_exception(func: Callable[[str], JudgeResult]):
    def wrapped(path: str):
        try:
            return func(path)
        except Exception as e:
            return JudgeResult(func.__name__, False, str(e))

    return wrapped


class TermLogger(ILogger):
    def __init__(self) -> None:
        self.has_failed = False

    def exec_func(self, func: Callable[[str], JudgeResult], ws_path: str) -> bool:
        result = wrap_exception(func)(ws_path)
        if result.success:
            print(f"[{result.title}]", colored("OK", "green"), flush=True)
        else:
            print(f"[{result.title}]", colored("Failed", "red"), flush=True)
            print(result.log)
            self.has_failed = True
        return result.success

    def end(self) -> None:
        if self.has_failed:
            exit(1)


class JsonLogger(ILogger):
    def __init__(self, json_path: str) -> None:
        self.json_path = os.path.abspath(json_path)
        self.results: List[JudgeResult] = []
        pass

    def exec_func(self, func: Callable[[str], JudgeResult], ws_path: str) -> bool:
        result = wrap_exception(func)(ws_path)
        self.results.append(result)
        return result.success

    def end(self) -> None:
        with open(self.json_path, "a") as f:
            f.write(json.dumps([result.__dict__ for result in self.results]) + "\n")
        self.results = []
