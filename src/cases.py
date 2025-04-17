from dataclasses import dataclass
from typing import Union, List
from correct import transform_article
import os
import random
import string
import json
from copy import deepcopy


@dataclass
class Case:
    input_doc_path: Union[None, str]
    need_redirect: bool
    input_citation: str
    output: Union[None, str]
    expect_output: Union[None, str]
    error: bool

    def generate_args(self) -> List[str]:
        args = ["-c", self.input_citation]

        if self.output is not None:
            args.extend(["-o", self.output])

        if not self.need_redirect:
            args.append(self.input_doc_path)
        else:
            args.append("-")

        return args

    def should_error(self) -> bool:
        return self.error


@dataclass
class MalformedCase:
    args: List[str]


# 8 random and valid isbn13
isbn_lists = [
    "9780262046305",  # INTRODUCTION TO. ALGORITHMS
    "9780321928429",  # C Primer Plus
    "9781292101767",  # Computer Systems: A Programmer's Perspective
    "9780132856201",  # Pearson Computer Networking, 8E
    "9781718503106",  # The Rust Programming Language
    "9780134610993",  # Artificial Intelligence: A Modern Approach
    "9780201103311",  # Programming Pearls
    "9780201006506",  # The Mythical Man-Month: Essays on Software Engineering
]
# 5 random website
website_lists = [
    "https://git-scm.com",
    "https://pytorch.org",
    "https://json.nlohmann.me",
    "https://code.visualstudio.com",
    "https://www.jetbrains.com/clion",
]

# 3 random articles
article_lists = [
    {
        "id": "yu2024accelerating_wwwwwwwwwwww",
        "type": "article",
        "title": "Accelerating Text-to-Image Editing via Cache-Enabled Sparse Diffusion Inference",
        "author": "Yu, Zihao and Li, Haoyang and Fu, Fangcheng and Miao, Xupeng and Cui, Bin",
        "journal": "Proceedings of the AAAI Conference on Artificial Intelligence",
        "volume": 38,
        "issue": 15,
        "year": 2024,
    },
    {
        "id": "liu2024infocon_kkkkkkkkkkk",
        "type": "article",
        "title": "InfoCon: Concept Discovery with Generative and Discriminative Informativeness",
        "author": "Ruizhe Liu and Qian Luo and Yanchao Yang",
        "journal": "The Twelfth International Conference on Learning Representations",
        "volume": 1,
        "issue": 2,
        "year": 2024,
    },
    {
        "id": "ho2020denoising_6666666666",
        "type": "article",
        "title": "Denoising Diffusion Probabilistic Models",
        "author": "Jonathan Ho and Ajay Jain and Pieter Abbeel",
        "journal": "Conference on Neural Information Processing Systems",
        "volume": 1,  # not correct, just random ones
        "issue": 2,
        "year": 2020,
    },
]


def get_random_str(
    size, chars=string.ascii_letters + string.digits + string.punctuation + " \n\t"
) -> str:
    chars = chars.replace("[", "").replace("]", "")  # remove special characters...
    return "".join(random.choices(chars, k=size))


def get_random_json() -> dict:
    result = {"version": 1, "citations": []}
    book_num = random.randint(0, len(isbn_lists))
    website_num = random.randint(0, len(website_lists))

    random.shuffle(isbn_lists)
    random.shuffle(website_lists)
    books = isbn_lists[:book_num]
    websites = website_lists[:website_num]

    determined_id = "unique_since_too_long"
    # id length is from 1 to 20.
    ids = [
        get_random_str(
            random.randint(1, len(determined_id)), string.ascii_letters + string.digits
        )
        for _ in range(book_num + website_num + 10)  # +10 to prevent non-unique
    ]

    ids = list(set(ids))
    # In case worst things happen... (very unlikely)
    if len(ids) < book_num + website_num:
        num = book_num + website_num - len(ids)
        ids.extend([determined_id + str(i) for i in range(num)])
    ids = ids[: book_num + website_num]

    for i in range(book_num):
        result["citations"].append({"id": ids[i], "type": "book", "isbn": books[i]})

    for i in range(website_num):
        result["citations"].append(
            {"id": ids[book_num + i], "type": "webpage", "url": websites[i]}
        )

    result["citations"] += article_lists

    random.shuffle(result["citations"])
    return result


def generate_random_files(input_dir: str, citation_dir: str):
    offset = 10  # File name count from 10.
    for i in range(3):
        # Generate 3 correct files
        final_citation_dict = get_random_json()
        citations = final_citation_dict["citations"]
        citation_ids = [citation["id"] for citation in citations]
        final_input = ""
        for citation_id in citation_ids:
            content = get_random_str(random.randint(50, 100))
            final_input += content + "[" + citation_id + "]"
        final_input += get_random_str(random.randint(50, 100))

        with (
            open(os.path.join(citation_dir, str(offset + i) + ".txt"), "w") as citefile,
            open(os.path.join(input_dir, str(offset + i) + ".txt"), "w") as inputfile,
        ):
            json.dump(final_citation_dict, citefile)
            json.dump(final_input, inputfile)

        # delete necessary keys.
        def del_mutate(key, suffix):
            new_dict = deepcopy(final_citation_dict)
            if key is not None:
                del new_dict["citations"][random.randint(0, len(citation_ids) - 1)][key]
            else:
                curr_dict = new_dict["citations"][
                    random.randint(0, len(citation_ids) - 1)
                ]
                keys = list(curr_dict.keys())
                keys.remove("id")
                keys.remove("type")  # They're already tested.
                curr_dict.pop(random.choice(keys))

            with (
                open(
                    os.path.join(citation_dir, str(offset + i) + suffix + ".txt"), "w"
                ) as citefile,
                open(
                    os.path.join(input_dir, str(offset + i) + suffix + ".txt"), "w"
                ) as inputfile,
            ):
                json.dump(new_dict, citefile)
                json.dump(final_input, inputfile)

        del_mutate("id", "_mut1")
        del_mutate("type", "_mut2")
        del_mutate(None, "_mut3")

        # change type of necessary keys
        def change_mutate(key, suffix):
            new_dict = deepcopy(final_citation_dict)
            mutpos = new_dict["citations"][random.randint(0, len(citation_ids) - 1)]

            if key is None:
                key = random.choice(list(mutpos.keys()))
            if type(mutpos[key]) is str:
                mutpos[key] = (
                    1 if random.random() < 0.5 else [1, 2, 3]
                )  # mutate to int or list
            elif type(mutpos[key]) is int:
                mutpos[key] = (
                    "You're fooled" if random.random() < 0.5 else {"You": "Great"}
                )  # mutate to str or dict

            with (
                open(
                    os.path.join(citation_dir, str(offset + i) + suffix + ".txt"), "w"
                ) as citefile,
                open(
                    os.path.join(input_dir, str(offset + i) + suffix + ".txt"), "w"
                ) as inputfile,
            ):
                json.dump(new_dict, citefile)
                json.dump(final_input, inputfile)

        change_mutate(None, "_mut4")
        change_mutate("type", "_mut5")  # mutate type to some wrong things...

        # make some citations absent.
        def citation_wrong_mutate(suffix):
            new_dict = deepcopy(final_citation_dict)
            del new_dict["citations"][random.randint(0, len(citation_ids) - 1)]

            with (
                open(
                    os.path.join(citation_dir, str(offset + i) + suffix + ".txt"), "w"
                ) as citefile,
                open(
                    os.path.join(input_dir, str(offset + i) + suffix + ".txt"), "w"
                ) as inputfile,
            ):
                json.dump(new_dict, citefile)
                json.dump(final_input, inputfile)

        citation_wrong_mutate("_mut6")

        # make bracket unmatched.
        def input_wrong_mutate(suffix):
            new_input = deepcopy(final_input)
            pos = random.randint(0, len(new_input))
            new_input = new_input[:pos] + "[" + new_input[pos:]  # Add unmatched '['

            with (
                open(
                    os.path.join(citation_dir, str(offset + i) + suffix + ".txt"), "w"
                ) as citefile,
                open(
                    os.path.join(input_dir, str(offset + i) + suffix + ".txt"), "w"
                ) as inputfile,
            ):
                json.dump(final_citation_dict, citefile)
                json.dump(new_input, inputfile)

        input_wrong_mutate("_mut7")


def get_cases(input_dir: str, citation_dir: str) -> List[Union[Case, MalformedCase]]:
    input_dir, citation_dir = os.path.abspath(input_dir), os.path.abspath(citation_dir)
    cases = []

    for filename in os.listdir(input_dir):
        input_path, citation_path = (
            os.path.join(input_dir, filename),
            os.path.join(citation_dir, filename),
        )
        assert (
            filename.endswith(".txt")
            and os.path.isfile(input_path)
            and os.path.isfile(citation_path)
        )

        with open(input_path, "r") as file:
            input_str = file.read()
        output_path = "answer" + filename
        expect_output = transform_article(input_str, citation_path)
        expect_output, error = expect_output.result, not expect_output.success

        # -c citation_path -o output_path input_file
        cases.append(
            Case(input_path, False, citation_path, output_path, expect_output, error)
        )
        # -c citation_path input_file
        cases.append(Case(input_path, False, citation_path, None, expect_output, error))
        # -c citation_path -o output_path -
        cases.append(
            Case(input_path, True, citation_path, output_path, expect_output, error)
        )
        # -c citation_path -
        cases.append(Case(input_path, True, citation_path, None, expect_output, error))

    valid_input, valid_citation = (
        os.path.join(input_dir, "1.txt"),
        os.path.join(citation_dir, "1.txt"),
    )
    invalid_input, invalid_citation = (
        os.path.join(input_dir, "10086.txt"),
        os.path.join(citation_dir, "10086.txt"),
    )

    # Input paths not exist:
    cases.extend(
        [
            Case(invalid_input, False, valid_citation, None, None, True),
            Case(invalid_input, False, valid_citation, "non-exist.txt", None, True),
        ]
    )

    # Citation paths not exist:
    cases.extend(
        [
            Case(valid_input, False, invalid_citation, None, None, True),
            Case(valid_input, False, invalid_citation, "non-exist.txt", None, True),
        ]
    )

    # Both paths not exist
    cases.extend(
        [
            Case(invalid_input, False, invalid_citation, None, None, True),
            Case(invalid_input, False, invalid_citation, "non-exist.txt", None, True),
        ]
    )

    # Then malformed ones...
    cases.extend(
        [
            MalformedCase([]),
            MalformedCase(["stray"]),
            MalformedCase(["more", "stray"]),
            MalformedCase(["--unrecognized"]),
            MalformedCase(["--dramatic", "unrecognized"]),
            MalformedCase(["-o"]),
            MalformedCase(["-c"]),
            MalformedCase(["-o", "a.txt", "-o", "b.txt", valid_input]),
            MalformedCase(["-c", valid_citation, "-c", valid_citation, valid_input]),
        ]
    )

    return cases


if __name__ == "__main__":
    # generate_random_files("./inputs", "./citations")
    cases = get_cases("./inputs", "./citations")

    for case in filter(lambda i: isinstance(i, Case), cases):
        if case.input_doc_path is not None:
            print(case.input_doc_path)
        if case.input_str is not None and case.output is not None:
            print(case.expect_output)

    # article = "The book [1] is a great book. The article [3] is also a classic. View [2] for more info."
    # citation_path = "./citations/1.txt"
