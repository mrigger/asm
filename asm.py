import sqlite3
import argparse
import os
import subprocess
import urllib.request, json
import datetime
import re
import time

parser = argparse.ArgumentParser(description='Manipulate the inline assembler database.')

parser = argparse.ArgumentParser()
parser.add_argument('database', metavar='database', help="path to the sqlite3 database")
parser.add_argument('command', choices=['categories', 'new-project-entry'])
parser.add_argument('--file',help='a file argument')
args = parser.parse_args()

conn = sqlite3.connect(args.database)
c = conn.cursor()


def print_sub_cat(super_id, tabs="\t"):
   """ display sub categories of a certain id. """
   for row in c.execute('select * from ApplicationCategory where SUPER_ID =?;', (str(super_id),)).fetchall():
      print(tabs + row[1])
      print_sub_cat(tabs + '\t', row[0])

def display_application_cats():
    """ Recursively displays all application categories. """
    rows = c.execute('select * from ApplicationCategory where SUPER_ID IS NULL;')
    for row in rows.fetchall():
        super_cat = row[1]
        print(super_cat)
        print_sub_cat(row[0])

def get_last_commit_hash(path):
    process = subprocess.Popen(['git', 'rev-parse', 'HEAD'], cwd=path, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    hash = stdout.decode().strip('\n')
    return hash

def get_git_commit_count(path):
    """ Gets the number of commits without merges from a Git repository. """
    process = subprocess.Popen(['git', 'rev-list', 'HEAD', '--count', '--no-merges'], cwd=path, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    number = stdout.decode().strip("\n")
    return int(number)

def get_git_commiter_count(path):
    """ Gets the number of committers from a Git repository. """
    process = subprocess.Popen(['git', 'shortlog', '-sn'], cwd=path, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    committers = stdout.decode()
    return len(committers.split('\n'))

def get_first_last_commit_date(path):
    """ Gets the first and repository commit as a timestamp. """
    # %at specifies a UNIX time stamp
    process = subprocess.Popen(['git', 'log', '--format=%at'], cwd=path, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    log = stdout.decode().strip('\n').split('\n')
    last = int(log[0])
    first = int(log[-1])
    return (first, last)

def get_git_url(path):
    """ Gets the origin URL of a Git repository. """
    process = subprocess.Popen(['git', 'config', '--get', 'remote.origin.url'], cwd=path, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    url = stdout.decode().strip("\n")
    if url.startswith("https://github.com"):
        return url
    else:
        print(url + " is not a valid url!")
        exit(-1)

def get_c_cpp_h_assembly_loc(path):
    """ Gets the LOC of header and C files using cloc. """
    try:
        process = subprocess.Popen(['cloc', '.'], cwd=path, stdout=subprocess.PIPE)
    except FileNotFoundError:
        print("Failed to call cloc (see https://github.com/AlDanial/cloc), please install.")
        exit(-1)
    stdout, _ = process.communicate()
    lines = stdout.decode().split('\n')
    c_lines = 0
    h_lines = 0
    cpp_lines = 0
    assembly_lines = 0
    for line in lines:
        c_match = re.match(r'C \s+\d+\s+\d+\s+\d+\s+(\d+)', line, re.X)
        if c_match:
            c_lines = int(c_match.groups()[0])
        h_match = re.match(r'C/C\+\+\sHeader\s+\d+\s+\d+\s+\d+\s+(\d+)', line, re.X)
        if h_match:
            h_lines = int(h_match.groups()[0])
        cpp_match = re.match(r'C\+\+\s+\d+\s+\d+\s+\d+\s+(\d+)', line, re.X)
        if cpp_match:
            cpp_lines = int(cpp_match.groups()[0])
        assembly_match = re.match(r'Assembly\s+\d+\s+\d+\s+\d+\s+(\d+)', line, re.X)
        if assembly_match:
            assembly_lines = int(assembly_match.groups()[0])
    return (c_lines, cpp_lines, h_lines, assembly_lines)

def insert_project_entry(dirname):
    if not os.path.isdir(dirname):
        print(dirname + " is not a directory!")
        exit(-1)
    dirs = dirname.rstrip(os.sep).split(os.sep)
    github_url = get_git_url(dirname)
    commit_count = get_git_commit_count(dirname)
    committers_count = get_git_commiter_count(dirname)
    (first_date, last_date) = get_first_last_commit_date(dirname)
    project_name = dirs[-1]
    organization_name = github_url.split('/')[-2]
    #today = datetime.datetime.today()
    (c_loc, cpp_loc, h_loc, assembly_loc) = get_c_cpp_h_assembly_loc(dirname)
    last_hash = get_last_commit_hash(dirname)
    # retrieve information from Github
    github_json_url = "https://api.github.com/repos/%s/%s" % (organization_name, project_name)
    with urllib.request.urlopen(github_json_url) as url:
        data = json.loads(url.read().decode())
        stargazers = data['stargazers_count']
        forks = data['forks_count']
        open_issues = data['open_issues_count']
        description = data['description']
        subscribers = data['subscribers_count']
        creation_date = datetime.datetime.strptime(data['created_at'], "%Y-%m-%dT%H:%M:%SZ").timestamp()
        language = data['language']
        query = """insert into GithubProject(
                GITHUB_PROJECT_NAME,
                GITHUB_URL,
                GITHUB_DESCRIPTION,
                GITHUB_NR_STARGAZERS,
                GITHUB_NR_SUBSCRIBERS,
                GITHUB_NR_FORKS,
                GITHUB_NR_OPEN_ISSUES,
                GITHUB_REPO_CREATION_DATE,
                GITHUB_LANGUAGE,

                PULL_HASH,
                PULL_DATE,

                CLOC_LOC_C,
                CLOC_LOC_H,
                CLOC_LOC_ASSEMBLY,
                CLOC_LOC_CPP,

                GIT_NR_COMMITS,
                GIT_NR_COMMITTERS,
                GIT_FIRST_COMMIT_DATE,
                GIT_LAST_COMMIT_DATE)

                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                """
        c.execute(query,
                (project_name,
                github_url,
                description,
                stargazers,
                subscribers,
                forks,
                open_issues,
                datetime.datetime.fromtimestamp(creation_date).strftime('%Y-%m-%d'),
                language,

                last_hash,
                datetime.datetime.now().strftime('%Y-%m-%d'),

                c_loc,
                h_loc,
                assembly_loc,
                cpp_loc,

                commit_count,
                committers_count,
                datetime.datetime.fromtimestamp(first_date).strftime('%Y-%m-%d'),
                datetime.datetime.fromtimestamp(last_date).strftime('%Y-%m-%d'))
                )
        conn.commit()


if args.command == 'categories':
    display_application_cats()
elif args.command == 'new-project-entry':
  if args.file is None:
      print("no --file arg")
      exit(-1)
  insert_project_entry(args.file)
