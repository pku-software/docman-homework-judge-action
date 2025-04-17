import argparse
import os
import shutil
import time
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from docman_judge.cases import generate_random_files, get_cases
from docman_judge.judge import build
from docman_judge.judge import test as test_by_case
from docman_judge.log import ILogger, JsonLogger, TermLogger


def judge(path: str, input_cases_dir: Path, citation_dir: Path, output_dir: Path, logger: ILogger):
    if logger.exec_func(build, path):
        cases = get_cases(input_cases_dir, citation_dir, output_dir)
        num_cases = len(cases)

        time_start = time.time()
        for i, case in enumerate(cases):
            print(f"Testing {i + 1}/{num_cases} [time escaped: {time.time() - time_start:.2f}s]...")

            def test(p: str):
                return test_by_case(p, case)

            logger.exec_func(test, path)
    logger.end()


def main():
    buildin_data = files("docman_judge.data")
    buildin_data_inputs = buildin_data / "inputs"
    buildin_data_citations = buildin_data / "citations"

    parser = argparse.ArgumentParser(description="RJSJ Docman Homework Judge Program")
    parser.add_argument("workspaces", nargs="*", help="workspace path")
    parser.add_argument("--batch", dest="batch_file", help="a file containing a list of workspace paths")
    parser.add_argument("--log", dest="log_file", help="a file to save the judge result")
    parser.add_argument("--input_dir", help="where test cases comes from", default=buildin_data_inputs)
    parser.add_argument(
        "--citation_dir", help="where citation for test cases comes from", default=buildin_data_citations
    )

    args = parser.parse_args()
    assert os.path.isdir(args.input_dir) and os.path.isdir(args.citation_dir)

    if args.log_file:
        logger = JsonLogger(args.log_file)
    else:
        logger = TermLogger()

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tmp_input_dir = tmpdir / "inputs"
        tmp_citation_dir = tmpdir / "citations"
        tmp_output_dir = tmpdir / "outputs"

        shutil.copytree(args.input_dir, tmp_input_dir)
        shutil.copytree(args.citation_dir, tmp_citation_dir)
        tmp_output_dir.mkdir(parents=True, exist_ok=True)

        generate_random_files(tmp_input_dir, tmp_citation_dir)

        if args.batch_file:
            assert os.path.isfile(args.batch)
            with open(args.batch_file, "r") as f:
                for line in f:
                    judge(line.strip(), tmp_input_dir, tmp_citation_dir, tmp_output_dir, logger)
        else:
            for arg in args.workspaces:
                judge(arg, tmp_input_dir, tmp_citation_dir, tmp_output_dir, logger)


if __name__ == "__main__":
    main()
