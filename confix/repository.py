from urllib.parse import urlencode

import requests

REPOSITORY_URL = 'https://proxy-groups.idefix64.fr/main.php'


def fetch_repository_categories(url=REPOSITORY_URL):
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


def search_repository_groups(category_id=None, query=None):
    """Return search results"""

    data = {
        'action': 'groups',
        'verified': 1,
    }

    if category_id:
        data['category_id'] = category_id

    if query:
        data['query'] = query

    url = REPOSITORY_URL + '?' + urlencode(data)

    results = requests.get(url)
    try:
        return results.json()
    except:
        return []


def upload_group(group_name, domains):
    """Create an unverified group"""

    url = REPOSITORY_URL + '?action=create'

    try:
        requests.post(url, {
            'name': group_name,
            'domains': ','.join(domains),
        })
        return True
    except requests.exceptions.RequestException as e:
        print(e)
        return False
