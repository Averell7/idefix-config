from urllib.parse import urlencode

import requests

REPOSITORY_URL = 'https://proxy-groups.idefix64.fr/main.php'


def fetch_repository_list(url=REPOSITORY_URL):
    """Fetch the list of categories"""

    result = requests.get(url + '?action=categories')
    if result.ok:
        return result.json()
    else:
        return None


def download_group_file(path):
    """Download the group ini file"""

    path = path.replace('http://', 'https://')  # Force https

    result = requests.get(path)
    return result.content


def search_repository_groups(category_id, query=None):
    """Return search results"""

    data = {
        'action': 'groups',
        'category_id': category_id,
        'verified': 1,
    }
    if query:
        data['query'] = query

    url = REPOSITORY_URL + '?' + urlencode(data)

    results = requests.get(url)
    return results.json()
