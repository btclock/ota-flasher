import json
import logging
import os
import requests
import wx
from typing import Callable
from datetime import datetime, timedelta

from app.utils import get_app_data_folder, keep_latest_versions

CACHE_FILE = get_app_data_folder() + '/cache.json'
CACHE_DURATION = timedelta(minutes=30)


class ReleaseChecker:
    '''Release Checker for firmware updates'''
    release_name = ""
    commit_hash = ""

    def __init__(self):
        self.progress_callback: Callable[[int], None] = None

    def load_cache(self):
        '''Load cached data from file'''
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_cache(self, cache_data):
        '''Save cache data to file'''
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)

    def fetch_latest_release(self):
        '''Fetch latest firmware release from GitHub'''
        repo = "btclock/btclock_v3"
        cache = self.load_cache()
        now = datetime.now()


        if 'latest_release' in cache and (now - datetime.fromisoformat(cache['latest_release']['timestamp'])) < CACHE_DURATION:
            latest_release = cache['latest_release']['data']
        else:
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            try:
                response = requests.get(url)
                response.raise_for_status()
                latest_release = response.json()
                cache['latest_release'] = {
                    'data': latest_release,
                    'timestamp': now.isoformat()
                }
                self.save_cache(cache)
            except requests.RequestException as e:
                raise ReleaseCheckerException(
                    f"Error fetching release: {e}") from e

        release_name = latest_release['tag_name']
        self.release_name = release_name

        filenames_to_download = ["lolin_s3_mini_213epd_firmware.bin",
                                 "lolin_s3_mini_29epd_firmware.bin",
                                 "btclock_v8_213epd_firmware.bin",
                                 "btclock_rev_b_213epd_firmware.bin",
                                 "littlefs.bin"]

        asset_urls = [asset['browser_download_url']
                      for asset in latest_release['assets'] if asset['name'] in filenames_to_download]

        if asset_urls:
            for asset_url in asset_urls:
                self.download_file(asset_url, release_name)

            ref_url = f"https://api.github.com/repos/{
                repo}/git/ref/tags/{release_name}"
            if ref_url in cache and (now - datetime.fromisoformat(cache[ref_url]['timestamp'])) < CACHE_DURATION:
                commit_hash = cache[ref_url]['data']

            else:
                response = requests.get(ref_url)
                response.raise_for_status()
                ref_info = response.json()
                if ref_info["object"]["type"] == "commit":
                    commit_hash = ref_info["object"]["sha"]
                else:
                    tag_url = f"https://api.github.com/repos/{
                        repo}/git/tags/{ref_info['object']['sha']}"
                    response = requests.get(tag_url)
                    response.raise_for_status()
                    tag_info = response.json()
                    commit_hash = tag_info["object"]["sha"]
                cache[ref_url] = {
                    'data': commit_hash,
                    'timestamp': now.isoformat()
                }
                self.save_cache(cache)

            self.commit_hash = commit_hash

            return self.release_name
        else:
            raise ReleaseCheckerException(
                f"File {filenames_to_download} not found in latest release")

    def download_file(self, url, release_name):
        '''Downloads Fimware Files'''
        local_filename = f"{release_name}_{url.split('/')[-1]}"
       
        if os.path.exists(f"{get_app_data_folder()}/{local_filename}"):
            return

        response = requests.get(url, stream=True)
        total_length = response.headers.get('content-length')
        keep_latest_versions(get_app_data_folder(), 2)

        if total_length is None:
            raise ReleaseCheckerException("No content length header")
        else:
            total_length = int(total_length)
            chunk_size = 1024
            num_chunks = total_length // chunk_size
            with open(f"{get_app_data_folder()}/{local_filename}", 'wb') as f:
                for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        progress = int((i / num_chunks) * 100)
                        if callable(self.progress_callback):
                            self.progress_callback(progress)

                if callable(self.progress_callback):
                    self.progress_callback(100)


class ReleaseCheckerException(Exception):
    pass
