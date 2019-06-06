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
<<<<<<< HEAD
    try:
        with urlopen(path) as request:
            if request.status != 200:
                return None

            return request.read()
    except HTTPError:
        return None
=======
    result = requests.get(path)
    return result.content
>>>>>>> parent of 33023a4... Remove requests in favour of urllib
