import re
import tomlkit
from sources import make_source

from ocflib.infra.github import GitRepo
from ocflib.infra.github import GithubCredentials

def update_version(line: str, ver: str):
    pattern = re.compile("(?<=:= )(.*)$")
    return pattern.sub(ver, line)

def get_local_makefile(filepath: str):
    with open(filepath, "r") as makefile:
        lines = makefile.readlines()
        return lines

def write_local_makefile(filepath: str, lines):
    with open(filepath, 'w') as makefile:
        for line in lines:
            makefile.write(str(line))

def process(repo, software):
    regex = re.compile(software["regex"])
    content = repo.get_file(software["file"])
    current = next(iter(regex.findall(content)), None)

    if current == None:
        print("[Warning] Unable to find current version for", software["name"], "in", software["file"])
        return

    backend = make_source(software["type"], software["id"])
    backend.refresh_source()
    latest = backend.get_latest()

    if latest != current:
        branch_name = f"u-{software['name']}-{latest}"
        base_branch = "master" # TODO: Allow custom branch names, such as the more modern "main".

        for branch in list(repo.github.get_branches()):
            if branch.name == branch_name:
                print("[Info] Branch already exists, no need to update.")
                return
        print(f"[Info] Updating {software['name']} from {current} to {latest}.")
        content = regex.sub(latest, content)
        print("[Info] Creating new branch.")
        repo.modify_and_branch(base_branch, branch_name, f"automatically bump version to {latest}", software["file"], content)
        #print(base_branch, branch_name, f"automatically bump version to {latest}", software["file"], content)
        print("[Info] Making pull request.")
        changelog_url = software["changelog"].format(latest)
        prbody = f"""
This pull request was automatically generated. Be sure to test it before merging! :)
You can find a changelog at {changelog_url}
"""
        repo.github.create_pull(title=f"[Automatic] Update {software['name']} from {current} to {latest}.", body=prbody, head=branch_name, base=base_branch)
        #print(f"[Automatic] Update {software['name']} from {current} to {latest}.", prbody, branch_name, base_branch)

def main():
    config = None
    with open("../config.toml", "r") as configfile:
        config = tomlkit.parse(configfile.read())
    if config == None:
        raise Exception("Failed to read config file.")
    
    gh_creds = GithubCredentials(token=config["settings"]["github_api_key"])

    print("Checking for updates across all repos in the file 'repos'.")
    for repo in config["repo"]:
        gh = GitRepo(repo["github_id"], gh_creds)
        for software in repo["software"]:
            process(gh, software)
    print("Update check complete.")

if __name__ == "__main__":
    main()
