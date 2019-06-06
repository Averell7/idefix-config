import json
from urllib.error import HTTPError
from urllib.request import urlopen

REPOSITORY_URL = 'http://proxy-groups.idefix64.fr/proxy-groups2.json'


def fetch_repository_list(url=REPOSITORY_URL):
    """Fetch the repository listing from the given url"""
    try:
        with urlopen(url) as request:
            if request.status != 200:
                return None

            return json.load(request)
    except HTTPError:
        return None


def download_group_file(path):
    """Download the group ini file"""
    try:
        with urlopen(path) as request:
            if request.status != 200:
                return None

            return request.read()
    except HTTPError:
        return None
