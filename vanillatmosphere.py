from utils import download_files, make_download_folder, load_repos, make_the_packs
repos = load_repos('repos.json')

def main():
    print("[Vanillatmosphere]")
    make_download_folder()

    for repo in repos:
        download_files(repo)

    make_the_packs()


if __name__ == "__main__":
    main()
