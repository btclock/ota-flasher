import os
import re
import wx


def count_versions(folder_path):
    versions = set()
    version_pattern = re.compile(r'^(\d+\.\d+\.\d+)')
    for file_name in os.listdir(folder_path):
        match = version_pattern.match(file_name)
        if match:
            versions.add(match.group(1))
    return len(versions)


def keep_latest_versions(folder_path, num_versions_to_keep=2):
    version_files = {}
    version_pattern = re.compile(r'^(\d+\.\d+\.\d+)')
    for file_name in os.listdir(folder_path):
        match = version_pattern.match(file_name)
        if match:
            version = match.group(1)
            if version not in version_files:
                version_files[version] = []
            version_files[version].append(file_name)

    versions_sorted = sorted(version_files.keys(), reverse=True)
    versions_to_remove = versions_sorted[num_versions_to_keep:]

    for version in versions_to_remove:
        for file_name in version_files[version]:
            os.remove(os.path.join(folder_path, file_name))

def get_app_data_folder():
    app = wx.GetApp()
    if app is None:
        app = wx.App(False)
        standard_paths = wx.StandardPaths.Get()
        app_data_dir = standard_paths.GetAppDocumentsDir() + "/BTClockOTA"
        app.Destroy()
        return app_data_dir
    else:
        standard_paths = wx.StandardPaths.Get()
        app_data_dir = standard_paths.GetAppDocumentsDir() + "/BTClockOTA"
    return app_data_dir