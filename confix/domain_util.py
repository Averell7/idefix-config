from urllib.parse import urlparse

import tldextract

extracter = tldextract.TLDExtract(cache_file='data/tld')


def extract_domain_parts(domain):
    """Extract domain name into its various parts"""
    return extracter(domain)


def extract_domain(url):
    """Extract the domain from the given full or partial URL"""

    if '://' not in url:
        url = '//' + url

    return urlparse(url, scheme='http').netloc
