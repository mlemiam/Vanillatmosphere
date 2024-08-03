import requests, re, os, zipfile, shutil, json, time

GITHUB_TOKEN = os.getenv('API_TOKEN')

def get_github_response(url):
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 403: 
        reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
        wait_time = reset_time - time.time()
        if wait_time > 0:
            print(f"[x] Rate limit exceeded. Waiting for {wait_time:.0f} seconds before retrying...")
            time.sleep(wait_time)
            response = requests.get(url, headers=headers)
    
    response.raise_for_status()
    return response

def load_repos(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"[x] {file_path} doesn't exist.")
        return []
    except json.JSONDecodeError:
        print(f"[x] JSON decoding error in {file_path} file.")
        return []

def prepare_download_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    else:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"[x] Error when deleting {file_path}: {e}")

def extract_zip(file_path, extract_to_folder):
    try:
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(extract_to_folder)
        print(f"Extracted {file_path} to {extract_to_folder}")
        return [os.path.join(extract_to_folder, name) for name in zip_ref.namelist()]
    except zipfile.BadZipFile:
        print(f"[x] {file_path} is not a valid zip file.")
        return []
    except Exception as e:
        print(f"[x] Error extracting {file_path}: {e}")
        return []

def download_and_process_assets(repo, folder):
    owner = repo["owner"]
    repo_name = repo["repo"]
    file_pattern = repo["file_pattern"]
    local_file_name = repo["local_file_name"]

    url = f"https://api.github.com/repos/{owner}/{repo_name}/releases"
    response = get_github_response(url)

    if response.status_code != 200:
        print(f"[x] Failed to fetch releases for {owner}/{repo_name}")
        return

    releases = response.json()

    if not releases:
        print(f"[x] No releases found for {owner}/{repo_name}")
        return

    latest_release = releases[0]

    if "assets" in latest_release:
        assets = latest_release["assets"]

        for asset in assets:
            asset_name = asset["name"]
            asset_url = asset["browser_download_url"]

            if re.search(file_pattern, asset_name):
                print(f"Downloading -> {asset_name}")

                response = get_github_response(asset_url)

                if response.status_code != 200:
                    print(f"[x] Failed to download {asset_name}")
                    continue

                destination_path = os.path.join(folder, asset_name)

                with open(destination_path, "wb") as file:
                    file.write(response.content)

                if asset_name.endswith(".zip"):
                    print(f"{asset_name} -> Extracting")
                    extracted_files = extract_zip(destination_path, folder)
                    
                    for extracted_file in extracted_files:
                        if os.path.isfile(extracted_file) and extracted_file.endswith(".zip"):
                            print(f"Nested ZIP found: {os.path.basename(extracted_file)}")
                            extract_zip(extracted_file, folder)
                            os.remove(extracted_file)
                    
                    os.remove(destination_path)
                else:
                    if asset_name == "fusee.bin":
                        bootloader_folder = os.path.join(folder, "bootloader")
                        payload_folder = os.path.join(bootloader_folder, "payloads")
                        print(f"Creating a folder -> {payload_folder}")
                        os.makedirs(payload_folder, exist_ok=True)
                        destination_file = os.path.join(payload_folder, asset_name)
                        print(f"Copying {asset_name} -> {payload_folder}")
                        shutil.copy(destination_path, destination_file)
    else:
        print(f"[x] No assets found in the latest release for {owner}/{repo_name}")


def main():
    download_folder = "artifact"
    repos = load_repos('repos.json')

    prepare_download_folder(download_folder)

    for repo in repos:
        download_and_process_assets(repo, download_folder)

if __name__ == "__main__":
    main()
