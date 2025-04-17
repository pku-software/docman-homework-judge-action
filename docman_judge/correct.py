import json
import re
import urllib
import urllib.parse
from dataclasses import dataclass
from typing import Dict, Tuple, Union

import requests


@dataclass
class Answer:
    result: str
    success: bool


def check_bracket_match(article: str) -> Tuple[list, bool]:
    bracket_match, ref_pair = [], []
    for result in re.finditer(r"\[|\]", article):
        capture = result.group(0)
        if capture == "[":
            bracket_match.append(result.start(0))
        elif capture == "]":
            if len(bracket_match) == 0:  # Too many ']'
                return ([], False)
            ref_pair.append((bracket_match.pop(), result.start(0)))

    if len(bracket_match) != 0:  # Too many '['
        return ([], False)
    return (ref_pair, True)


# Return ({id: citation}, success)
def check_citation(citation_path: str) -> Tuple[Dict[str, dict], bool]:
    with open(citation_path, "r") as file:
        citations = json.load(file)
    if "citations" not in citations:
        return ([], False)
    citations = citations["citations"]
    if type(citations) is not list:
        return ([], False)

    for citation in citations:
        if type(citation) is not dict or "id" not in citation or "type" not in citation:
            return ([], False)
        if type(citation["id"]) is not str or type(citation["type"]) is not str:
            return ([], False)
        if citation["type"] == "book":
            if "isbn" not in citation or type(citation["isbn"]) is not str:
                return ([], False)
        elif citation["type"] == "webpage":
            if "url" not in citation or type(citation["url"]) is not str:
                return ([], False)
        elif citation["type"] == "article":
            keys = [
                ("title", str),
                ("author", str),
                ("journal", str),
                ("volume", int),
                ("year", int),
                ("issue", int),
            ]
            for key in keys:
                if key[0] not in citation or type(citation[key[0]]) is not key[1]:
                    return ([], False)
        else:  # unrecognized type
            return ([], False)

    citation_ids = [citation["id"] for citation in citations]
    if len(set(citation_ids)) != len(citation_ids):  # non-unique id
        return ([], False)

    return ({citation["id"]: citation for citation in citations}, True)


def citation_info_to_str(citation) -> Union[None, str]:
    API_ENDPOINT = "http://docman.zhuof.wang"

    if citation["type"] == "book":
        result = requests.get(
            API_ENDPOINT + "/isbn/" + urllib.parse.quote(citation["isbn"], safe="")
        )
        result = json.loads(result.content.decode())
        if (
            "author" not in result
            or "title" not in result
            or "publisher" not in result
            or "year" not in result
        ):
            return None
        if (
            type(result["author"]) is not str
            or type(result["title"]) is not str
            or type(result["publisher"]) is not str
            or type(result["year"]) is not str
        ):
            return None

        return "[%s] book: %s, %s, %s, %s" % (
            citation["id"],
            result["author"],
            result["title"],
            result["publisher"],
            result["year"],
        )
    elif citation["type"] == "webpage":
        result = requests.get(
            API_ENDPOINT + "/title/" + urllib.parse.quote(citation["url"], safe="")
        )
        result = json.loads(result.content.decode())
        if "title" not in result or type(result["title"]) is not str:
            return None
        return "[%s] webpage: %s. Available at %s" % (
            citation["id"],
            result["title"],
            citation["url"],
        )
    elif citation["type"] == "article":
        return "[%s] article: %s, %s, %s, %d, %d, %d" % (
            citation["id"],
            citation["author"],
            citation["title"],
            citation["journal"],
            citation["year"],
            citation["volume"],
            citation["issue"],
        )


def transform_article(article: str, citation_path: str):
    ref_pairs, success = check_bracket_match(article)
    if not success:
        return Answer(None, False)

    citations, success = check_citation(citation_path)
    if not success:
        return Answer(None, False)

    exist_citations = []
    for begin, end in ref_pairs:
        curr_id = article[begin + 1 : end]
        if curr_id not in citations:  # id not exist
            return Answer(None, False)
        exist_citations.append(citations[curr_id])

    exist_citations.sort(key=lambda x: x["id"])
    reference_list_str = []
    for citation in exist_citations:
        result = citation_info_to_str(citation)
        if result is None:
            return Answer(None, False)
        reference_list_str.append(result)

    result = article + "\n\nReferences:\n" + "\n".join(reference_list_str)
    return Answer(result, True)
