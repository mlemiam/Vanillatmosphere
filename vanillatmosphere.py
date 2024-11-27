import requests, re, os, zipfile, shutil, json, time, pyfiglet, glob
from colorama import Fore, init

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

def prepare_download_folder():
    folders = ['artifact', 'artifact-legacy']
    for folder in folders:
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

def make_the_packs():
    
    print(Fore.MAGENTA + 'Copying configs files -> artifact')
    for item in glob.glob(os.path.join('configs', '*')):
        source_path = item
        destination_path = os.path.join('artifact', os.path.basename(item))

        if os.path.isdir(source_path):
            shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, destination_path)

    print(Fore.MAGENTA + "Editing boot.ini")
    boot_ini_path = 'artifact/boot.ini'

    with open(boot_ini_path, 'r') as file:
        content = file.read()

    for file_path in glob.glob('artifact/hekate_ctcaer_*.bin'):
        file_name = os.path.basename(file_path)
        content = content.replace('<payload>', file_name)

    with open(boot_ini_path, 'w') as file:
        file.write(content)

    print(Fore.MAGENTA + "Making boot.dat")
    shutil.copy(glob.glob('artifact/hekate_ctcaer_*.bin')[0], 'scripts/payload.bin')

    os.system("python scripts/tx_custom_boot.py scripts/payload.bin artifact/boot.dat")
    print(Fore.MAGENTA + "removing syspatch and somes shits and making a copy of artifact -> artifact-legacy")
    os.remove('scripts/payload.bin')

    shutil.copytree('artifact', 'artifact-legacy', dirs_exist_ok=True)

    sys_patch = [
        'artifact-legacy/atmosphere/contents/420000000000000B/',
        'artifact-legacy/config/'
    ]

    for path in sys_patch:
        shutil.rmtree(path)
    
    print(Fore.MAGENTA + "Editing hekate_ipl.ini to enable sigpatches patching")
    with open('artifact-legacy/bootloader/hekate_ipl.ini', 'r') as file:
        lines = file.readlines()

    modified_lines = []
    for line in lines:
        modified_line = re.sub(r'^\s*;\s*(.*)$', r'\1', line)
        modified_lines.append(modified_line)

    with open('artifact-legacy/bootloader/hekate_ipl.ini', 'w') as file:
        file.writelines(modified_lines)

    print(Fore.MAGENTA + "Downloading sigpatches from trusted source :3")

    response = requests.get('https://sigmapatches.su/sigpatches.zip', stream=True)
    if response.status_code == 200:
        with open('sigpatches.zip', 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    else:
        print(f'[x] Failed to download sigpatches :  {response.status_code}')
        exit()
    print(Fore.MAGENTA + "extracting sigpatches.zip to -> artifact-legacy")
    with zipfile.ZipFile("sigpatches.zip","r") as zip_ref:
        zip_ref.extractall("artifact-legacy/")

    os.remove('sigpatches.zip')

def main():
    init(autoreset=True)
    repos = load_repos('repos.json')
    
    font = pyfiglet.Figlet(font='big', width=100)

    print(Fore.CYAN+ font.renderText("Vanillatmosphere"))

    print(Fore.YELLOW + '[!] Preparing the download folder')
    prepare_download_folder()
    print(Fore.GREEN + '[*] Done.')

    print(Fore.YELLOW + '[!] Downloading all the files needed to make the pack')
    for repo in repos:
        download_and_process_assets(repo, "artifact")
    print(Fore.GREEN + '[*] Done.')
    print(Fore.YELLOW + '[!] Finishing the process by making 2 separate folders, artifact that use syspatch and artifact-legacy that use sigpatches.')
    make_the_packs()
    print(Fore.GREEN + '[*] Done. Thank you for using my script')

if __name__ == "__main__":
    main()
