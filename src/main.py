import argparse
from log import ILogger, TermLogger, JsonLogger
from judge import prepare, build, test as test_by_case
from cases import get_cases
import os

def judge(path: str, input_cases_dir: str, citation_dir: str, 
          expect_output_cases_dir: str, logger: ILogger):
    if logger.exec_func(prepare, path):
        if logger.exec_func(build, path):
            for case in get_cases(input_cases_dir, citation_dir, 
                                  expect_output_cases_dir):
                def test(p: str):
                    return test_by_case(p, case)
                logger.exec_func(test, path)
    logger.end()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='RJSJ Docman Homework Judge Program')
    parser.add_argument('workspaces', nargs='*', help='workspace path')
    parser.add_argument('--batch', dest='batch_file',
                        help='a file containing a list of workspace paths')
    parser.add_argument('--log', dest='log_file',
                        help='a file to save the judge result')
    parser.add_argument("--input_dir", help="where test cases comes from")
    parser.add_argument("--citation_dir", 
                        help="where citation for test cases comes from")
    parser.add_argument("--expect_output_dir", 
                        help="where correct test cases come from")

    args = parser.parse_args()
    assert(os.path.isdir(args.input_dir) and os.path.isdir(args.citation_dir) 
           and os.path.isdir(args.expect_output_dir) and os.path.isfile(args.batch))

    if args.log_file:
        logger = JsonLogger(args.log_file)
    else:
        logger = TermLogger()

    if args.batch_file:
        with open(args.batch_file, "r") as f:
            for line in f:
                judge(line.strip(), args.input_dir, args.citation_dir, args.expect_output_dir, logger)
    else:
        for arg in args.workspaces:
            judge(arg, args.input_dir, args.citation_dir, args.expect_output_dir, logger)