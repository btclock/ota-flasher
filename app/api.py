import time
import requests
import json
from threading import Thread


class ApiHandler:
    def identify_btclock(self, address):
        self.make_api_call(address, "api/identify")
        return

    def check_fs_hash(self, address):
        ret = self.run_api_call(address, "fs_hash.txt")
        return ret

    def get_settings(self, address):
        ret = json.loads(self.run_api_call(address, "api/settings"))
        return ret

    def make_api_call(self, address, path):
        thread = Thread(target=self.run_api_call, args=(address, path))
        thread.start()

    def run_api_call(self, address, path):
        try:
            url = f"http://{address}/{path}"
            response = requests.get(url)
            return response.text
        except requests.RequestException as e:
            print("error")
