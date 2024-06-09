import os
import requests
import wx
from typing import Callable

from app.utils import keep_latest_versions


class ReleaseChecker:
    '''Release Checker for firmware updates'''
    release_name = ""
    commit_hash = ""

    def __init__(self):
        self.progress_callback: Callable[[int], None] = None

    def fetch_latest_release(self):
        '''Fetch latest firmware release from GitHub'''
        repo = "btclock/btclock_v3"

        if not os.path.exists("firmware"):
            os.makedirs("firmware")
        filenames_to_download = ["lolin_s3_mini_213epd_firmware.bin",
                                 "btclock_rev_b_213epd_firmware.bin", "littlefs.bin"]
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            response = requests.get(url)
            response.raise_for_status()
            latest_release = response.json()
            release_name = latest_release['tag_name']
            self.release_name = release_name

            asset_url = None
            asset_urls = []
            for asset in latest_release['assets']:
                if asset['name'] in filenames_to_download:
                    asset_urls.append(asset['browser_download_url'])
            if asset_urls:
                for asset_url in asset_urls:
                    self.download_file(asset_url, release_name)
                ref_url = f"https://api.github.com/repos/{
                    repo}/git/ref/tags/{release_name}"
                response = requests.get(ref_url)
                response.raise_for_status()
                ref_info = response.json()
                if (ref_info["object"]["type"] == "commit"):
                    self.commit_hash = ref_info["object"]["sha"]
                else:
                    tag_url = f"https://api.github.com/repos/{
                        repo}/git/tags/{ref_info["object"]["sha"]}"
                    response = requests.get(tag_url)
                    response.raise_for_status()
                    tag_info = response.json()
                    self.commit_hash = tag_info["object"]["sha"]

                return self.release_name

            else:
                raise ReleaseCheckerException(
                    f"File {filenames_to_download} not found in latest release")
        except requests.RequestException as e:
            raise ReleaseCheckerException(
                f"Error fetching release: {e}") from e

    def download_file(self, url, release_name):
        '''Downloads Fimware Files'''
        local_filename = f"{release_name}_{url.split('/')[-1]}"
        response = requests.get(url, stream=True)
        total_length = response.headers.get('content-length')
        if not os.path.exists("firmware"):
            os.makedirs("firmware")
        if os.path.exists(f"firmware/{local_filename}"):
            return

        keep_latest_versions('firmware', 2)

        if total_length is None:
            raise ReleaseCheckerException("No content length header")
        else:
            total_length = int(total_length)
            chunk_size = 1024
            num_chunks = total_length // chunk_size
            with open(f"firmware/{local_filename}", 'wb') as f:
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
