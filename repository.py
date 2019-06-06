import requests

REPOSITORY_URL = 'http://proxy-groups.idefix64.fr/proxy-groups2.json'


def fetch_repository_list(url=REPOSITORY_URL):
    """Fetch the repository listing from the given url"""
    result = requests.get(url)
    if result.ok:
        return result.json()
    else:
        return None


def download_group_file(path):
    """Download the group ini file"""
    result = requests.get(path)
    return result.content
