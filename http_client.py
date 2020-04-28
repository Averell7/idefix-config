
import http.client


def get(ip, address, params={}, timeout=15):

            php_params = []
            for param in params :
                # TODO if extention = php
                php_params.append(param + "=" + params[param])
            address = address + "?" + "&".join(php_params)
            print("====>", address)

            h1 = http.client.HTTPConnection(ip, timeout=10)
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
            
def post():
    print("not yet implemented")
    return "not yet implemented"

