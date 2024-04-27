import requests, re, os, zipfile, shutil

download_folder = "artifact"

repos = [
    {
        "owner": "Atmosphere-NX",
        "repo": "Atmosphere",
        "file_pattern": r"^atmosphere-(\d+(\.\d+))((\.\d+))-[a-zA-Z]+-[a-zA-Z0-9]+\+hbl-[0-9]*\.[0-9]+[0-9]*\.[0-9]+\+hbmenu-[0-9]*\.[0-9]+[0-9]*\.[0-9]+\.zip$",
        "local_file_name": "atmosphere.zip",
    },
    {
        "owner": "Atmosphere-NX",
        "repo": "Atmosphere",
        "file_pattern": r"^fusee\.bin$",
        "local_file_name": "fusee.bin",
    },
    {
        "owner": "CTCaer",
        "repo": "hekate",
        "file_pattern": r"^hekate_ctcaer_[0-9]+\.[0-9]+\.[0-9]+_Nyx_[0-9]+\.[0-9]+\.[0-9]+(_v2)?\.zip$",
        "local_file_name": "hekate.zip",
    },
    {
        "owner": "fortheusers",
        "repo": "hb-appstore",
        "file_pattern": r"^switch-extracttosd\.zip$",
        "local_file_name": "hb-appstore.zip",
    },
]

if not os.path.exists(download_folder):
    os.makedirs(download_folder)
else:
    shutil.rmtree(download_folder)

for repo in repos:
    owner = repo["owner"]
    repo_name = repo["repo"]
    file_pattern = repo["file_pattern"]
    local_file_name = repo["local_file_name"]

    url = f"https://api.github.com/repos/{owner}/{repo_name}/releases"
    response = requests.get(url)
    releases = response.json()

    if releases:
        latest_release = releases[0] 

        if "assets" in latest_release:
            assets = latest_release["assets"]

            for asset in assets:
                asset_name = asset["name"]
                asset_url = asset["browser_download_url"]

                if re.search(file_pattern, asset_name):
                    print(f"Downloading -> {asset_name}")

                    response = requests.get(asset_url)

                    destination_path = os.path.join(download_folder, local_file_name)

                    with open(destination_path, "wb") as file:
                        file.write(response.content)

                    if asset_name.endswith(".zip"):
                        print(f"{asset_name} -> Extracting")

                        with zipfile.ZipFile(destination_path, "r") as zip_ref:
                            zip_ref.extractall(download_folder)

                        os.remove(destination_path)
                    else:
                        if asset_name == "fusee.bin":
                            bootloader_folder = os.path.join(download_folder, "bootloader")
                            payload_folder = os.path.join(bootloader_folder, "payloads")
                            os.makedirs(payload_folder, exist_ok=True)
                            destination_file = os.path.join(payload_folder, asset_name)
                            shutil.copy(destination_path, destination_file)

        else:
            print("No file found\n")
