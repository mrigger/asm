#!/usr/bin/env python3

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
parser.add_argument('command', choices=['categories', 'new-project-entry', 'download-project', 'add-asm-instruction', 'add-asm-sequence', 'add-project-asm-sequence', 'add-project-keywords', 'show-stats'])
parser.add_argument('--file',help='a file argument')
parser.add_argument('--instr',help='an instruction argument')
parser.add_argument('--keywords',help='specify keywords')
args = parser.parse_args()

conn = sqlite3.connect(args.database)
c = conn.cursor()

dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.join(dir, 'projects')
grep_exec = os.path.join(dir, 'grep.sh')

def print_sub_cat(super_id, tabs="\t"):
   """ display sub categories of a certain id. """
   rows = c.execute('select * from ApplicationCategory where SUPER_ID =?;', (str(super_id),)).fetchall()
   for row in rows:
      print(tabs + row[1])
      print_sub_cat(row[0], tabs + '\t')

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
    committers = stdout.decode("ISO-8859-1")
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

def get_project_dir(url):
    """ Map a Github URL to the local Github project directory. """
    (project_owner, project_name) = owner_project_from_github_url(url)
    project_dir_name = project_owner + '-' + project_name
    project_dir_name = os.path.join(project_dir, project_dir_name)
    return project_dir_name

def download_project(url, keywords=None):
    project_dir_name = get_project_dir(url)
    process = subprocess.Popen(['git', 'clone', url, project_dir_name], cwd=project_dir)
    process.communicate()
    insert_project_entry(os.path.join(project_dir, project_dir_name))
    add_keywords_to_project(url, keywords)

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

def owner_project_from_github_url(url):
    """ Extracts owner and project name from a Github URL. For example, for
        https://github.com/graalvm/sulong it returns the tuple (graalvm, sulong). """
    if not re.match('https://github.com/([a-zA-Z0-9-_]*)/[a-zA-Z0-9-_]*', url):
        print(str(url) + "is not a valid url!")
        exit(-1)
    elements = url.split('/')
    project_name = elements[-1]
    organization_name = elements[-2]
    return (organization_name, project_name)

def add_asm_instruction(instr, testcase=None):
    """ Inserts an instruction with a test case into the database. It reads the test case from the provided file and formats it using clang-format-3.6.
        If a test case for the instruction already exists, it will get updated.
    """
    if testcase is not None:
        process = subprocess.Popen(['clang-format-3.6', '--style=LLVM', testcase], stdout=subprocess.PIPE)
        stdout, _ = process.communicate()
        formatted_testcase = stdout.decode()
    else:
        formatted_testcase = ''

    result = c.execute('SELECT TEST_CASE from AsmInstruction WHERE INSTRUCTION = ?', (instr,)).fetchone()
    if result is None:
        c.execute('insert into AsmInstruction(INSTRUCTION, TEST_CASE) VALUES(?, ?)', (instr, formatted_testcase))
    else:
        print("update existing test case:")
        print(result[0])
        print("with new one:")
        print(formatted_testcase)
        c.execute('update AsmInstruction set TEST_CASE=? where INSTRUCTION =?', (formatted_testcase, instr))
    conn.commit()

def add_asm_sequence(instrs, testcase, note=''):
    """ Inserts an ordered list of assembly instruction and creates the individual assembly instructions if they do not exist yet. """
    result = c.execute('SELECT ID from AsmSequence WHERE INSTRUCTIONS=?', (instrs, )).fetchone()
    if result is not None:
        print("asm sequence already exists! skiping insertion")
        return
    instr_list = instrs.split(';')
    instr_ids = []
    for instr in instr_list:
        print(instr)
        result = c.execute('SELECT ID from AsmInstruction WHERE INSTRUCTION = ?', (instr,)).fetchone()
        if result is None:
            add_asm_instruction(instr)
            result = c.execute('SELECT ID from AsmInstruction WHERE INSTRUCTION = ?', (instr,)).fetchone()
        instr_ids += result
    i = 0
    c.execute('insert into AsmSequence(COMPOUND_TEST_CASE, NOTE, INSTRUCTIONS) VALUES (?, ?, ?)', (testcase, note, instrs))
    sequence_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    for instruction_id in instr_ids:
        c.execute('insert into AsmSequenceInstruction(INSTRUCTION_NUMBER, ASM_SEQUENCE_ID, ASM_INSTRUCTION_ID) VALUES(?, ?, ?)', (i, sequence_id, instruction_id))
        i += 1
    conn.commit()

def add_asm_sequence_in_project(sequence, filepath):
    splitted_path = filepath.split(os.sep)
    if splitted_path[0] != 'projects':
        print("please specify the path relative to the projects directory!")
        exit(-1)
    dir = os.path.dirname(os.path.realpath(__file__))
    absolute_path = os.path.join(dir, 'projects/' + splitted_path[1])
    github = get_git_url(absolute_path)
    print(github)
    project_id = get_project_id(github)
    add_asm_sequence(sequence, '')
    sequence_id = c.execute('SELECT ID from AsmSequence WHERE INSTRUCTIONS = ?', (sequence,)).fetchone()[0]
    project_file = os.sep.join(splitted_path[2:])
    c.execute('insert into AsmSequencesInGithubProject(IN_FILE, GITHUB_PROJECT_ID, ASM_SEQUENCE_ID) VALUES(?, ?, ?)', (project_file, project_id, sequence_id))
    conn.commit()

def get_project_id(github_url):
    return c.execute('select ID from GithubProject where GITHUB_URL=?', (github_url, )).fetchone()[0]

def insert_project_keyword(keyword):
    """ Inserts a project keyword if it does not exist. Returns the keyword id of the (potentially inserted) keyword. """
    keyword_id = c.execute('SELECT ID from ApplicationCategory WHERE NAME = ?', (keyword, )).fetchone()
    if keyword_id is None:
        c.execute('insert into ApplicationCategory(NAME) VALUES (?)', (keyword, ))
        return c.execute('SELECT last_insert_rowid()').fetchone()[0]
    else:
        return keyword_id[0]

def print_query_as_command(command, query):
    print('\\newcommand{\\%s}{%s}' % (command, c.execute(query).fetchone()[0], ))

def print_as_command(command, content):
    print('\\newcommand{\\%s}{%s}' % (command, content, ))


def show_stats():
    #print("Instruction count over all projects and sequences:")
    #for row in c.execute('SELECT AsmInstruction.ID, AsmInstruction.INSTRUCTION, SUM(AsmSequencesInGithubProject.NR_OCCURRENCES) total_count FROM AsmSequenceInstruction, AsmInstruction, AsmSequencesInGithubProject WHERE AsmInstruction.ID = AsmSequenceInstruction.ASM_INSTRUCTION_ID AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID GROUP BY AsmInstruction.INSTRUCTION, AsmInstruction.ID ORDER BY total_count DESC'):
    #    print("{:<20} {:<10}".format(row[1], row[2]))
    #    print("'%s' \t %d" % (row[1], row[2]))
    print("Number of times an instruction is contained in different projects:")
    for row in c.execute('SELECT AsmInstruction.ID, AsmInstruction.INSTRUCTION, (SELECT COUNT(DISTINCT AsmSequencesInGithubProject.Github_PROJECT_ID) FROM AsmSequenceInstruction, AsmSequencesInGithubProject WHERE AsmSequenceInstruction.ASM_INSTRUCTION_ID = AsmInstruction.ID AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID) count FROM AsmInstruction ORDER BY count desc;'):
        print("{:<20} {:<10}".format(row[1], row[2]))

    print('% how often an instruction appears in different projects')
    for row in c.execute('SELECT AsmInstruction.ID, AsmInstruction.INSTRUCTION, (SELECT COUNT(DISTINCT AsmSequencesInGithubProject.Github_PROJECT_ID) FROM AsmSequenceInstruction, AsmSequencesInGithubProject WHERE AsmSequenceInstruction.ASM_INSTRUCTION_ID = AsmInstruction.ID AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID) count FROM AsmInstruction ORDER BY count desc;'):
        instr_name = row[1].replace(' ', '')
        replacements = {
            '' : 'noInstr', # compiler/memory barrier
            '#' : 'comment', # asm comment
            'int$0x03' : 'intdebug', # debug interrupt
            'int$0x80' : 'intsystemcall', # system call interrupt
            'crc32' : 'crc',
            'cvtsd2si' : 'cvtsdtosi',
            'ud2' : 'ud'
        }
        instr_name = replacements.get(instr_name, instr_name)
        print_as_command(instr_name + 'ProjectCount', row[2])
    print('% total LOC of .c and .h files')
    print_query_as_command('loc', 'SELECT SUM(CLOC_LOC_H+CLOC_LOC_C) FROM GithubProject;')
    print('% total number of projects')
    print_query_as_command('nrProjects', 'SELECT COUNT(*) FROM GithubProject;')
    print('% number of projects where we checked the usage of inline assembly')
    print_query_as_command('nrCheckedProjects', 'SELECT COUNT(*) from GithubProject WHERE ANALYZED_FOR_INLINE_ASM=1')
    print('% number of projects where we did not yet check the usage of inline assembly')
    print_query_as_command('nrUncheckedProjects', 'SELECT COUNT(*) from GithubProject WHERE ANALYZED_FOR_INLINE_ASM!=1')
    print('% projects that contain one or more inline assembly sequences')
    print_query_as_command('nrProjectsWithInlineAsm', 'SELECT ((SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) from AsmSequencesInGithubProject) + (SELECT COUNT(*) from GithubProject WHERE ANALYZED_FOR_INLINE_ASM!=1))')
    print('% average number of inline assembly snippets computed over the set of projects that use inline assembly')
    print_query_as_command('avgNrInlineAssemblySnippets', 'SELECT AVG(number) FROM (SELECT SUM(NR_OCCURRENCES) as number FROM AsmSequencesInGithubProject GROUP BY GITHUB_PROJECT_ID);')
    print('% average number of UNIQUE (on a file basis) inline assembly snippets computed over the set of projects that use inline assembly')
    print_query_as_command('avgNrFileuniqueInlineAssemblySnippets', 'SELECT AVG(number) FROM (SELECT COUNT(*) as number FROM AsmSequencesInGithubProject GROUP BY GITHUB_PROJECT_ID);')
    print('% total number of inline assembly snippets')
    print_query_as_command('nrInlineAssemblySnippets', 'SELECT SUM(NR_OCCURRENCES) FROM AsmSequencesInGithubProject;')
    # SELECT AsmInstruction.ID, AsmInstruction.INSTRUCTION, (SELECT COUNT(DISTINCT AsmSequencesInGithubProject.Github_PROJECT_ID) FROM AsmSequenceInstruction, AsmSequencesInGithubProject WHERE AsmSequenceInstruction.ASM_INSTRUCTION_ID = AsmInstruction.ID AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID) FROM AsmInstruction;
    # SELECT * FROM AsmSequenceInstruction WHERE AsmSequenceInstruction.ASM_INSTRUCTION_ID = 9
    # SELECT COUNT(DISTINCT AsmSequencesInGithubProject.Github_PROJECT_ID) FROM AsmSequenceInstruction, AsmSequencesInGithubProject WHERE AsmSequenceInstruction.ASM_INSTRUCTION_ID = 7 AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID

def add_keywords_to_project(url, keywords):
    keyword_tokens = keywords.split(',')
    project_id = get_project_id(url)
    for keyword in keyword_tokens:
        keyword_id = insert_project_keyword(keyword)
        existing_record = c.execute('SELECT * FROM ApplicationCategoriesPerProject WHERE ApplicationCategoryID = ? AND GithubProjectID = ?', (keyword_id, project_id))
        if project_id is not None:
            c.execute('insert into ApplicationCategoriesPerProject(ApplicationCategoryID, GithubProjectID) VALUES(?, ?)', (keyword_id, project_id))
    conn.commit()

def insert_project_entry(dirname):
    if not os.path.isdir(dirname):
        print(dirname + " is not a directory!")
        exit(-1)
    dirs = dirname.rstrip(os.sep).split(os.sep)
    github_url = get_git_url(dirname)
    commit_count = get_git_commit_count(dirname)
    committers_count = get_git_commiter_count(dirname)
    (first_date, last_date) = get_first_last_commit_date(dirname)
    (organization_name, project_name) = owner_project_from_github_url(github_url)
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

def grep_project(url):
    """ Executes the grep.sh script on the project directory. """
    project = get_project_dir(url)
    print(grep_exec + ' ' + project)
    process = subprocess.Popen(['bash', grep_exec, project])
    process.communicate()

if args.command == 'categories':
    display_application_cats()
elif args.command == 'new-project-entry':
    if args.file is None:
        print("no --file arg")
        exit(-1)
    insert_project_entry(args.file)
    grep_project(args.file)
elif args.command == 'download-project':
    if args.file is None:
        print("no --file arg")
        exit(-1)
    download_project(args.file, args.keywords)
    grep_project(args.file)
elif args.command == 'add-asm-instruction':
    if args.file is None:
        print("no --file arg")
        exit(-1)
    if args.instr is None:
        print("no --instr arg")
        exit(-1)
    add_asm_instruction(args.instr, args.file)
elif args.command == 'add-asm-sequence':
    if args.instr is None:
        print("no --instr arg")
        exit(-1)
    add_asm_sequence(args.instr, args.file)
elif args.command == 'add-project-asm-sequence':
    if args.instr is None:
        print("no --instr arg")
        exit(-1)
    add_asm_sequence_in_project(args.instr, args.file)
elif args.command == 'add-project-keywords':
    if args.file is None:
        print("no --file arg")
        exit(-1)
    if args.keywords is None:
        print("no --keywords arg")
        exit(-1)
    add_keywords_to_project(args.file, args.keywords)
elif args.command == 'show-stats':
    show_stats()

