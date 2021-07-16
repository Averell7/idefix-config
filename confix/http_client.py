import http.client
from urllib.parse import urlencode


def get(ip, address, params=None, timeout=15):
    if not params:
        params = {}
    params = urlencode(params)
    address = address + "?" + params
    print("====>", address)

    h1 = http.client.HTTPConnection(ip, timeout=timeout)
    try:
        h1.connect()
    except:
        h1.close()
        return
    h1.request("GET", address)
    res = h1.getresponse()
    content = ""
    if res.status == 200:
        content = res.read().decode("cp850")

    h1.close()
    print("====>", content)
    return content


def post(ip, address, data, timeout=15):
    if not data:
        data = {}

    data = urlencode(data)
    print("====>", address)

    h1 = http.client.HTTPConnection(ip, timeout=timeout)
    try:
        h1.connect()
    except:
        h1.close()
        return
    h1.request("POST", address, data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    res = h1.getresponse()
    content = ""
    if res.status == 200:
        content = res.read().decode("cp850")

    h1.close()
    print("====>", content)
    return content
