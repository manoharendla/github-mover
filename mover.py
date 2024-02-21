import json
import os
import requests
import base64
import zipfile
import shutil
import subprocess
import logging

from pathlib import Path

log = logging.getLogger(__name__)
log.addHandler(logging.FileHandler("mover.log"))
log.setLevel(logging.INFO)

from argparse import ArgumentParser as AP

def check_org_exists(github_instance, org, headers):
    url = f"https://{github_instance}/orgs/{org}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return True
    return False

def check_repo_exists(github_instance, org, repo, headers):
    url = f"https://{github_instance}/repos/{org}/{repo}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return True
    return False

def check_remote_branch_exists(github_instance, org, repo, branch, headers):
    url = f"https://{github_instance}/repos/{org}/{repo}/branches/{branch}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return True
    return False

def validator(github_instance, org, repo, branch, headers):
    if not check_org_exists(github_instance, org, headers):
        raise RuntimeError(f"Org {org} does not exist in {github_instance}")
    if not check_repo_exists(github_instance, org, repo, headers):
        raise RuntimeError(f"Repo {repo} does not exist in {org}")
    if not check_remote_branch_exists(github_instance, org, repo, branch, headers):
        raise RuntimeError(f"Branch {branch} does not exist in {repo}")
    return True
        
def download_repo(source_github_instance, source_org, source_repo, source_branch, source_headers):
    if validator(source_github_instance, source_org, source_repo, source_branch, source_headers):
        url = f"https://{source_github_instance}/repos/{source_org}/{source_repo}/zipball/{source_branch}"
        response = requests.get(url, headers=source_headers)
        response.raise_for_status()
        if response.status_code == 200:
            with open(f"{source_repo}.zip", "wb") as f:
                f.write(response.content)
                print(f"Downloaded {source_repo} to {source_repo}.zip")
                print(os.listdir())
def create_githhub_organization(destination_github_instance, destination_org, destination_headers):
    if not check_org_exists(destination_github_instance, destination_org, destination_headers):
        url = f"https://{destination_github_instance}/orgs/{destination_org}"
        data = {
            "login": destination_org
        }
        response = requests.post(url, headers=destination_headers, json=data)
        response.raise_for_status()
        if response.status_code == 201:
            print(f"Organization {destination_org} created in {destination_github_instance}")
    else:
        raise RuntimeError(f"Organization {destination_org} already exists in {destination_github_instance}")
    
def create_repo(destination_github_instance, destination_org, destination_repo, destination_branch, destination_headers):
    if not check_repo_exists(destination_github_instance, destination_org, destination_repo, destination_headers):
        url = f"https://{destination_github_instance}/orgs/{destination_org}/repos"
        data = {
            "name": destination_repo,
            "private": False,
            "auto_init": True,
            "default_branch": destination_branch
        }
        response = requests.post(url, headers=destination_headers, json=data)
        response.raise_for_status()
        if response.status_code == 201:
            print(f"Repo {destination_repo} created in {destination_org}")
    else:
        raise RuntimeError(f"Repo {destination_repo} already exists in {destination_org}")

def create_remote_branch(destination_github_instance, destination_org, destination_repo, destination_branch, destination_headers):
    if not check_remote_branch_exists(destination_github_instance, destination_org, destination_repo, destination_branch, destination_headers):
        url = f"https://{destination_github_instance}/repos/{destination_org}/{destination_repo}/git/refs"
        data = {
            "ref": f"refs/heads/{destination_branch}",
            "sha": "" }
        response = requests.post(url, headers=destination_headers, json=data)
        response.raise_for_status()
        if response.status_code == 201:
            print(f"Branch {destination_branch} created in {destination_repo}")
    
def source_authenticate_github():
    source_token = os.environ.get("SOURCE_GITHUB_TOKEN")
    if not source_token:
        raise ValueError(f"No source token found, required environment variable: SOURCE_GITHUB_TOKEN for source github instance SOURCE_GITHUB_INSTANCE")
    return source_token

def destination_authenticate_github():
    destination_token = os.environ.get("DESTINATION_GITHUB_TOKEN")
    if not destination_token:
        raise ValueError(f"No destination token found, required environment variable: DESTINATION_GITHUB_TOKEN for destination github instance DESTINATION_GITHUB_INSTANCE")
    return destination_token

def remove_everything_except_git(directory):
    print(f"list of files in {directory} are: {os.listdir(directory)}")
    for item in os.listdir(directory):
        if item != ".git":
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            else:
                shutil.rmtree(item_path)
    print(f"After list of files in {directory} are: {os.listdir(directory)}")


def replace_string_in_files(directory):
    valid_files = ["Dockerfile", "Makefile", "README.md", "Jenkinsfile"]
    print(f"current file path: {Path(__file__).resolve().parent}")
    print(f"curent working directory: {os.getcwd()}")
    print(f"list of files in {directory} are: {os.listdir()}")
    with open(os.path.join(Path(__file__).resolve().parent,"replace.json"), "r") as f:
        replace_dict = json.load(f)
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file in valid_files:
                    file_path = os.path.join(root, file)
                    with open(file_path, "r") as f:
                        content = f.read()
                        for key, value in replace_dict.items():
                            content = content.replace(key, value)
                            print(f"content: {content}")
                    with open(file_path, "w") as f:
                        f.write(content)



def clone_and_push_the_repo(source_org, source_repo, source_branch, destination_org, destination_repo, destination_branch, destination_github_instance, username="Mano", email="manoharendla277@gmail.com"):
    extract_to = "zip_extracted"
    if os.path.exists(destination_repo):
        shutil.rmtree(destination_repo)

    try:
        repository_url = f'https://manoharendla277:{destination_authenticate_github()}@github.com/{destination_org}/{destination_repo}.git' # Change here
        subprocess.run(["git", "clone", repository_url])
    except Exception as e:
        print(f"Error: {e}")
    
    remove_everything_except_git(destination_repo)

    if not os.path.exists(extract_to):
        os.makedirs(extract_to)
        # Open the ZIP file for reading
    with zipfile.ZipFile(f"{source_repo}.zip", 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    print("list file in zip_extracted: ", os.listdir(extract_to))

    for root, dirs, files in os.walk(extract_to):
        for dir_name in dirs:
            if dir_name.startswith(source_org):
                source_folder = os.path.join(root, dir_name)
                for item in os.listdir(source_folder):
                    source_item = os.path.join(source_folder, item)
                    destination_item = os.path.join(destination_repo, item)
                    shutil.move(source_item, destination_item)
                shutil.rmtree(source_folder)
    
    replace_string_in_files(destination_repo)
    repo_path = os.path.join(os.getcwd(), destination_repo)
    subprocess.run(["git", "add", "."], cwd=repo_path)
    subprocess.run(["git", "commit", "-m", "Initial commit using python Automation"], cwd=repo_path)
    subprocess.run(["git", "config", "--global", "user.name", username], check=True)
    subprocess.run(["git", "config", "--global", "user.email", email], check=True)
    subprocess.run(["git", "push", "origin", f"{source_branch}:{destination_branch}"], cwd=repo_path)
     

def upload_repo(source_org, source_repo, source_branch, destination_org, destination_repo, destination_branch, destination_github_instance, destination_headers):
    if not check_org_exists(destination_github_instance, destination_org, destination_headers):
        create_githhub_organization(destination_github_instance, destination_org, destination_headers)
    
    if not check_repo_exists(destination_github_instance, destination_org, destination_repo, destination_headers):
        create_repo(destination_github_instance, destination_org, destination_repo, destination_branch, destination_headers)
    
    clone_and_push_the_repo(source_org, source_repo, source_branch, destination_org, destination_repo, destination_branch, destination_github_instance)

    #push_to_github(destination_org, destination_repo, destination_branch)

 


if __name__ == "__main__":
    parser = AP(description="Move repos from one org to another")
    parser.add_argument("source_github_instance", help="Source github instance", default="github.com")
    parser.add_argument("destination_github_instance", help="Destination github instance", default="github.com")
    parser.add_argument("source_org", help="Source org", default="mano-python")
    parser.add_argument("destination_org", help="Destination org", default="mano-python")
    parser.add_argument("source_repo", help="Source repo", default="testrepo3")
    parser.add_argument("destination_repo", help="Destination repo", default="testrepo4")
    parser.add_argument("source_branch", help="Source branch", default="main")
    parser.add_argument("destination_branch", help="Destination branch", default="main")
    args = parser.parse_args()

    source_headers = {'Authorization': f'token {source_authenticate_github()}'}
    destination_headers = {'Authorization': f'token {destination_authenticate_github()}'}
    download_repo(args.source_github_instance, args.source_org, args.source_repo, args.source_branch, source_headers)
    upload_repo(args.source_org, args.source_repo, args.source_branch, args.destination_org, args.destination_repo, args.destination_branch, args.destination_github_instance, destination_headers)
        






