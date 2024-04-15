import json
import re
from dataclasses import dataclass
from typing import Union, Tuple, Dict
import urllib.parse
import urllib.request
import urllib.response
import requests
import urllib

@dataclass
class Answer:
    result: str
    success: bool

def check_bracket_match(article: str) -> Tuple[list, bool]:
    bracket_match, ref_pair = [], []
    for result in re.finditer(r"\[|\]", article):
        capture = result.group(0)
        if capture == '[':
            bracket_match.append(result.start(0))
        elif capture == ']':
            if len(bracket_match) == 0: # Too many ']'
                return ([], False)
            ref_pair.append((bracket_match.pop(), result.start(0)))

    if len(bracket_match) != 0: # Too many '['
        return ([], False)
    return (ref_pair, True)

# Return ({id: citation}, success)
def check_citation(citation_path: str) -> Tuple[Dict[str, dict], bool]:
    citations = json.load(open(citation_path, "r"))
    if "citations" not in citations:
        return ([], False)
    citations = citations["citations"]
    if type(citations) != list:
        return ([], False)

    for citation in citations:
        if type(citation) != dict or "id" not in citation or "type" not in citation:
            return ([], False)
        if citation["type"] == "book":
            if "isbn" not in citation or type(citation["isbn"]) != str:
                return ([], False)
        elif citation["type"] == "webpage":
            if "url" not in citation or type(citation["url"]) != str:
                return ([], False)
        elif citation["type"] == "article":
            keys = [("title", str), ("author", str), ("journal", str), 
                    ("volume", int), ("year", int), ("issue", int)]
            for key in keys:
                if key[0] not in citation or type(citation[key[0]]) != key[1]:
                    return ([], False)
        else: # unrecognized type
            return ([], False)

    citation_ids = [citation["id"] for citation in citations]
    if len(set(citation_ids)) != len(citation_ids): # non-unique id
        return ([], False)

    return ({citation["id"]:citation for citation in citations}, True)

def citation_info_to_str(citation) -> Union[None, str]:
    API_ENDPOINT = "http://docman.lcpu.dev"

    if citation["type"] == "book":
        result = requests.get(API_ENDPOINT + "/isbn/" + urllib.parse.quote(citation["isbn"], safe=''))
        result = json.loads(result.content.decode())
        if "author" not in result or "title" not in result or\
            "publisher" not in result or "year" not in result:
            return None
        return "[%s] book: %s, %s, %s, %s" % (citation["id"], result["author"], 
                                              result["title"], result["publisher"], result["year"])
    elif citation["type"] == "webpage":
        result = requests.get(API_ENDPOINT + "/title/" + urllib.parse.quote(citation["url"], safe=''))
        result = json.loads(result.content.decode())
        if "title" not in result:
            return None
        return "[%s] webpage: %s. Available at %s" % (citation["id"], result["title"], citation["url"])
    elif citation["type"] == "article":
        return "[%s] article: %s, %s, %s, %d, %d, %d" % \
            (citation["id"], citation["author"], citation["title"], citation["journal"], 
             citation["year"], citation["volume"], citation["issue"])

def transform_article(article: str, citation_path: str):
    ref_pairs, success = check_bracket_match(article)
    if not success:
        return Answer(None, False)

    citations, success = check_citation(citation_path)
    if not success:
        return Answer(None, False)

    exist_citations = []
    for begin, end in ref_pairs:
        curr_id = article[begin + 1: end]
        if curr_id not in citations: # id not exist
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
