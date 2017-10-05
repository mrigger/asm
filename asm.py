#!/usr/bin/env python3

# check: SELECT * FROM AsmSequencesInGithubProject WHERE AsmSequencesInGithubProject.ASM_SEQUENCE_ID NOT IN (SELECT ID FROM AsmSequence)

import sqlite3
import argparse
import os
import subprocess
import urllib.request, json
import datetime
import re
import time
import sys

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

def check_for_invalid_instructions(instrs):
    """ Checks that a list of instruction does not contain any invalid instructions (not the right format) """
    for instr in instrs:
        # Check for x86 instruction prefixes
        # see http://www.c-jump.com/CIS77/CPU/x86/X77_0240_prefix.htm
        if instr in ['lock', 'rep', 'repne']:
            print('The instruction sequence contains the instruction prefix ' + instr + '.')
            print('Please specifiy the prefix as part of the next instruction, for example, "lock xadd" instead of "lock;xadd".')
            exit(-1)
        if instr == 'rep nop':
            print('Please insert "rep nop" as pause (MNEMONIC is 0)!')
            exit(-1)
        if instr == 'xchg':
            print('Please insert "xchg" as "lock xchg"!')
        # check the interrupt format
        if re.match('int .*', instr):
            if not re.match('int \$0x[0-9a-f]{2}', instr):
                print('Please use the format "int $0xa3" to specify numbers in int instructions! ' + instr)
                exit(-1)

def add_asm_sequence(instrs, testcase, note=''):
    """ Inserts an ordered list of assembly instruction and creates the individual assembly instructions if they do not exist yet. """
    result = c.execute('SELECT ID from AsmSequence WHERE INSTRUCTIONS=?', (instrs, )).fetchone()
    if result is not None:
        print("asm sequence already exists! skiping insertion")
        return
    instr_list = instrs.replace(',', ';').split(';')
    check_for_invalid_instructions(instr_list)
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
    c.execute('insert into AsmSequencesInGithubProjectUnfiltered(IN_FILE, GITHUB_PROJECT_ID, ASM_SEQUENCE_ID) VALUES(?, ?, ?)', (project_file, project_id, sequence_id))
    conn.commit()

def get_project_id(github_url):
    return c.execute('select ID from GithubProjectUnfiltered where GITHUB_URL=?', (github_url, )).fetchone()[0]

def insert_project_keyword(keyword):
    """ Inserts a project keyword if it does not exist. Returns the keyword id of the (potentially inserted) keyword. """
    keyword_id = c.execute('SELECT ID from ApplicationCategory WHERE NAME = ?', (keyword, )).fetchone()
    if keyword_id is None:
        c.execute('insert into ApplicationCategory(NAME) VALUES (?)', (keyword, ))
        return c.execute('SELECT last_insert_rowid()').fetchone()[0]
    else:
        return keyword_id[0]

def print_query_as_command(command, query, roundn=False, percentage=False):
    print_as_command(command, c.execute(query).fetchone()[0], roundn, percentage)

def print_as_command(command, content, roundn=False, percentage=False):
    formats = '%.1f' if roundn or percentage else '%s'
    if percentage:
        formats = formats + '\%%'
    print(('\\newcommand{\\%s}{' + formats + '}') % (command, content, ))

def escape_latex(str):
    return str.replace('#', '\#').replace('$', '\$')

def print_table_start(name, columns, caption):
    print("\\newcommand{\\%s}{" % name)
    print("\\begin{table}[]")
    print("\\caption{%s}" % caption)
    print("\\centering")
    print("\\begin{tabular}{l", end='')
    for i in range(columns-1): print("|l", end='')
    print("}")

def print_table_end(label):
    print("""\\end{tabular}
\\label{%s}
\\end{table}}""" % label)

def print_instruction_table(nr_instructions=3):
    # print latex table
    print_table_start(name="instructiontable", columns=3, caption="The most common instructions")
    print("instruction & \# & contained in \% projects with inline assembly \\\\ \hline")
    for row in c.execute('SELECT * FROM InstructionFrequencies WHERE count >= ' + str(nr_instructions) + ' ORDER BY count desc;'):
        print("%s & %s & %.1f\%% \\\\" % (escape_latex(row[1]), row[2], row[3]))
    print_table_end(label="tbl:common-instructions")

def print_mnemonic_table(nr_projects=5):
    """ Prints the table of project-unique instruction sequences that contain non-mnemonic instructions. """
    print_table_start("mnemonictable", columns=2, caption="Instruction sequences that did not use mnemonics and where used in at least " + str(nr_projects) + " projects")
    print("instruction & \# non-mnemonic usages \\\\ \hline")
    for row in c.execute('SELECT INSTRUCTIONS, COUNT (DISTINCT AsmSequencesInAnalyzedGithubProjects.GITHUB_PROJECT_ID) count FROM AsmSequencesInAnalyzedGithubProjects, AsmSequence WHERE MNEMONIC = 0 AND AsmSequencesInAnalyzedGithubProjects.ASM_SEQUENCE_ID = AsmSequence.ID GROUP BY AsmSequence.ID HAVING count >= ? ORDER BY count DESC;', (nr_projects,)):
        print("%s & %s \\\\" % (escape_latex(row[0]), row[1]))
    print_table_end("tbl:no-mnemonics")

def print_domain_table(nr_projects=7):
    print_table_start(name="domaintable", columns=3, caption="Domains of inline assembly projects (each domain containing more than " + str(nr_projects-1) + " projects)")
    print("domain & \# projects & \% of projects \\\\ \hline")
    for row in c.execute('SELECT COUNT(*) as count, MAIN_CATEGORY, COUNT(*) * 100.0/(SELECT COUNT(*) FROM GithubProjectWithInlineAsm) as perc FROM GithubProjectWithInlineAsm GROUP BY MAIN_CATEGORY HAVING count >= ? ORDER BY count DESC', (nr_projects, )):
        replacements = {
            'TODO' : 'misc',
        }
        name = replacements.get(row[1], row[1])
        print("%s & %s & %.1f \\\\" % (name, row[0], row[2]))
    print_table_end("tbl:domains")

def print_lock_table(nr_projects=1):
    print_table_start(name="locktable", columns=2, caption="Number of projects that use atomic instructions (with at least " + str(nr_projects) + " using them)")
    print("instruction & \# \\\\ \hline")
    for row in c.execute('SELECT * FROM InstructionFrequencies WHERE INSTRUCTION LIKE "lock%" AND count >= ?', (nr_projects, )):
        print("%s & %s \\\\" % (row[1], row[2]))
    print_table_end(label="tbl:lock")

def print_set_byte_table(nr_projects=1):
    print_table_start(name="settable", columns=2, caption="Number of projects that use set-on-condition instructions (with at least " + str(nr_projects) + " using them)")
    print("instruction & \# \\\\ \hline")
    for row in c.execute('SELECT * FROM InstructionFrequencies WHERE INSTRUCTION LIKE "set%" AND count >= ?', (nr_projects, )):
        print("%s & %s \\\\" % (row[1], row[2]))
    print_table_end(label="tbl:settable")

def print_rep_table(nr_projects=1):
    print_table_start(name="repttable", columns=2, caption="Number of projects that instructions with \code{rep} prefixes (with at least " + str(nr_projects) + " using them)")
    print("instruction & \# \\\\ \hline")
    for row in c.execute('SELECT * FROM InstructionFrequencies WHERE (INSTRUCTION LIKE "rep%" or INSTRUCTION LIKE "cld") AND count >= ?', (nr_projects, )):
        print("%s & %s \\\\" % (row[1], row[2]))
    print_table_end(label="tbl:repttable")

def print_control_flow_table(nr_projects=1):
    print_table_start(name="controlflowtable", columns=2, caption="Number of projects that use control-flow instructions (with at least " + str(nr_projects) + " using them)")
    print("instruction & \# \\\\ \hline")
    for row in c.execute('SELECT * FROM InstructionFrequencies WHERE INSTRUCTION LIKE "j%" OR INSTRUCTION IN ("cmp", "test") AND count >= ?', (nr_projects, )):
        print("%s & %s \\\\" % (row[1], row[2]))
    print_table_end(label="tbl:controlflow")

def print_arithmetic_table(nr_projects=1):
    print_table_start(name="arithmetictable", columns=2, caption="Number of projects that use arithmetic instructions (with at least " + str(nr_projects) + " using them)")
    print("instruction & \# \\\\ \hline")
    for row in c.execute("SELECT * FROM InstructionFrequencies WHERE INSTRUCTION IN ('xor', 'add', 'or', 'sub', 'and', 'inc', 'dec', 'mul', 'adc', 'dec', 'neg', 'lea') AND count >= ?", (nr_projects, )):
        print("%s & %s \\\\" % (row[1], row[2]))
    print_table_end(label="tbl:arithmetic")

def database_integrity_tests():
    if c.execute('SELECT COUNT(*) FROM AsmSequencesInGithubProjectUnfiltered WHERE ASM_SEQUENCE_ID NOT IN (SELECT ID FROM AsmSequence)').fetchone()[0] != 0:
        print('Dangling AsmSequence entry!')
        exit(-1)
    # not supported by the Python sqlite3 bindings?
    #if c.execute('SELECT * FROM AsmSequencesInGithubProjectUnfiltered WHERE CODE REGEXP "rep([; \t\n])*nop" AND MNEMONIC = 1').fetchone()[0] != 0:
    if c.execute('SELECT COUNT(*) FROM AsmSequencesInGithubProjectUnfiltered WHERE MNEMONIC = 1 AND (CODE LIKE "%rep; nop%" or CODE LIKE "%rep;nop%")').fetchone()[0] != 0:
        print('rep nop with MNEMONIC = 0')
        exit(-1)
    if c.execute('SELECT COUNT(*) FROM AsmSequencesInGithubProjectUnfiltered WHERE CODE LIKE "%.byte%" AND MNEMONIC = 1').fetchone()[0] != 0:
        print('.byte with MNEMONIC = 0')
        exit(-1)
    if c.execute('SELECT COUNT(*) FROM AsmInstruction WHERE INSTRUCTION LIKE "j%" AND CONTROL_FLOW = 0').fetchone()[0] != 0:
        print('jump instruction with CONTROL_FLOW = 0')
        exit(-1)

def create_scatter_plot_data(output_dir):
    sys.stdout = open(output_dir + '/scatterplot_git_commits.csv', 'w+')
    print('nr_commits;nr_inline_snippets')
    for row in c.execute('SELECT GIT_NR_COMMITS, SUM(NR_OCCURRENCES) AS nr FROM GithubProjectCompletelyAnalyzed, AsmSequencesInAnalyzedGithubProjects WHERE GithubProjectCompletelyAnalyzed.ID = AsmSequencesInAnalyzedGithubProjects.GITHUB_PROJECT_ID GROUP BY GITHUB_PROJECT_ID'):
        print('%d;%d' % row)
    sys.stdout.close()

    sys.stdout = open(output_dir + '/scatterplot_git_nr_committers.csv', 'w+')
    print('nr_commiters;nr_inline_snippets')
    for row in c.execute('SELECT GIT_NR_COMMITTERS, SUM(NR_OCCURRENCES) AS nr FROM GithubProjectCompletelyAnalyzed, AsmSequencesInAnalyzedGithubProjects WHERE GithubProjectCompletelyAnalyzed.ID = AsmSequencesInAnalyzedGithubProjects.GITHUB_PROJECT_ID GROUP BY GITHUB_PROJECT_ID'):
        print('%d;%d' % row)
    sys.stdout.close()

    sys.stdout = open(output_dir + '/scatterplot_git_stargazers.csv', 'w+')
    print('github_stargazers;nr_inline_snippets')
    for row in c.execute('SELECT GITHUB_NR_STARGAZERS, SUM(NR_OCCURRENCES) AS nr FROM GithubProjectCompletelyAnalyzed, AsmSequencesInAnalyzedGithubProjects WHERE GithubProjectCompletelyAnalyzed.ID = AsmSequencesInAnalyzedGithubProjects.GITHUB_PROJECT_ID GROUP BY GITHUB_PROJECT_ID'):
        print('%d;%d' % row)
    sys.stdout.close()

    sys.stdout = open(output_dir + '/scatterplot_first_commit_date.csv', 'w+')
    print('first_commit_date;nr_inline_snippets')
    for row in c.execute('SELECT GIT_FIRST_COMMIT_DATE, SUM(NR_OCCURRENCES) AS nr FROM GithubProjectCompletelyAnalyzed, AsmSequencesInAnalyzedGithubProjects WHERE GithubProjectCompletelyAnalyzed.ID = AsmSequencesInAnalyzedGithubProjects.GITHUB_PROJECT_ID GROUP BY GITHUB_PROJECT_ID'):
        print('%s;%d' % row)
    sys.stdout.close()

    sys.stdout = open(output_dir + '/scatterplot_macro_assembly.csv', 'w+')
    print('macro_assembly_loc;nr_inline_snippets')
    for row in c.execute('SELECT CLOC_LOC_ASSEMBLY, SUM(NR_OCCURRENCES) AS nr FROM GithubProjectCompletelyAnalyzed, AsmSequencesInAnalyzedGithubProjects WHERE GithubProjectCompletelyAnalyzed.ID = AsmSequencesInAnalyzedGithubProjects.GITHUB_PROJECT_ID GROUP BY GITHUB_PROJECT_ID'):
        print('%s;%d' % row)
    sys.stdout.close()

    sys.stdout = open(output_dir + '/scatterplot_github_nr_forks.csv', 'w+')
    print('github_nr_forks;nr_inline_snippets')
    for row in c.execute('SELECT GITHUB_NR_FORKS, SUM(NR_OCCURRENCES) AS nr FROM GithubProjectCompletelyAnalyzed, AsmSequencesInAnalyzedGithubProjects WHERE GithubProjectCompletelyAnalyzed.ID = AsmSequencesInAnalyzedGithubProjects.GITHUB_PROJECT_ID GROUP BY GITHUB_PROJECT_ID'):
        print('%s;%d' % row)
    sys.stdout.close()

def show_stats(output_dir):
    #print("Instruction count over all projects and sequences:")
    #for row in c.execute('SELECT AsmInstruction.ID, AsmInstruction.INSTRUCTION, SUM(AsmSequencesInGithubProject.NR_OCCURRENCES) total_count FROM AsmSequenceInstruction, AsmInstruction, AsmSequencesInGithubProject WHERE AsmInstruction.ID = AsmSequenceInstruction.ASM_INSTRUCTION_ID AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID GROUP BY AsmInstruction.INSTRUCTION, AsmInstruction.ID ORDER BY total_count DESC'):
    #    print("{:<20} {:<10}".format(row[1], row[2]))
    #    print("'%s' \t %d" % (row[1], row[2]))

    print("Number of times an instruction is contained in different projects:")
    for row in c.execute('SELECT * FROM InlineAssemblyInstructionsInProjects ORDER BY count desc;'):
        print("{:<20} {:<10}".format(row[1], row[2]))

    #max_commits = c.execute('SELECT MAX(GIT_NR_COMMITS) FROM GithubProjectWithInlineAsm').fetchone()[0]
    #nr_buckets = 20
    #count = c.execute('SELECT GIT_NR_COMMITS FROM GithubProjectWithInlineAsm ', (lower, upper, lower, upper)).fetchone()[0]
    #for commits in range(0, nr_buckets):
    #    lower = max_commits/nr_buckets * commits
    #    upper = max_commits/nr_buckets * (commits + 1)
    #    count = c.execute('SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM GithubProject WHERE GIT_NR_COMMITS > ? AND GIT_NR_COMMITS <= ?) FROM GithubProjectWithInlineAsm WHERE GIT_NR_COMMITS > ? AND GIT_NR_COMMITS <= ?', (lower, upper, lower, upper)).fetchone()[0]
        #number_projects = c.execute('SELECT COUNT(*) FROM GithubProject WHERE GIT_NR_COMMITS > ? AND GIT_NR_COMMITS <= ?', (lower, upper)).fetchone()[0]
    #    print(str(lower) + ";" + str(upper) + ";" + str(count))
    #sys.stdout.close()

    create_scatter_plot_data(output_dir)

    sys.stdout = open(output_dir + '/commands.tex', 'w+')
    print_instruction_table()
    print_mnemonic_table()
    print_domain_table()
    print_lock_table()
    print_set_byte_table()
    print_control_flow_table()
    print_rep_table()
    print_arithmetic_table()

    print('% how often an instruction appears in different projects')
    for row in c.execute('SELECT * FROM InlineAssemblyInstructionsInProjects ORDER BY count desc;'):
        instr_name = row[1].replace(' ', '')
        replacements = {
            '' : 'noInstr', # compiler/memory barrier
            '#' : 'comment', # asm comment
            'int$0x03' : 'intdebug', # debug interrupt
            'int$0x80' : 'intsystemcall', # system call interrupt
            'crc32' : 'crc',
            'cvtsd2si' : 'cvtsdtosi',
            'ud2' : 'ud',
            '<name>' : 'declarativeName',
            '<register>' : 'register'
        }
        instr_name = replacements.get(instr_name, instr_name)
        print_as_command(instr_name + 'ProjectCount', row[2])
    # SELECT COUNT(*) / (SELECT COUNT(*)*1.0 FROM GithubProject WHERE GITHUB_NR_STARGAZERS > 1000) FROM GithubProjectWithInlineAsm WHERE GITHUB_NR_STARGAZERS > 1000
    print('% total LOC of .c and .h files')
    print_query_as_command('mloc', 'SELECT SUM(CLOC_LOC_H+CLOC_LOC_C)/1000000 FROM GithubProject;')
    print('% total number of projects')
    print_query_as_command('nrProjects', 'SELECT COUNT(*) FROM GithubProject;')#
    print('% total number of unique instructions')
    print_query_as_command('nrUniqueInstructions', 'SELECT COUNT(*) FROM InstructionFrequencies WHERE percentage > 0')
    checked_down_to_stars = '850'
    print('% checked down to # stars')
    print_query_as_command('githubStarsPopularity', 'SELECT ' + checked_down_to_stars)
    print('% checked projects by popularity')
    print_query_as_command('nrSelectedProjectsByPopularity', 'SELECT COUNT(*) FROM GithubProject WHERE GithubProject.GITHUB_NR_STARGAZERS >= ' + checked_down_to_stars)
    print('% checked projects by domain')
    print_query_as_command('nrSelectedProjectsByDomain', 'SELECT COUNT(*) FROM GithubProject WHERE GithubProject.GITHUB_NR_STARGAZERS < ' + checked_down_to_stars)

    print('\n%############ statistics about checked projects')
    print('% number of projects where we checked the usage of inline assembly')
    print_query_as_command('nrCheckedProjects', 'SELECT COUNT(*) FROM GithubProjectCompletelyAnalyzed')
    print('% percentage of all projects where we checked the usage of inline assembly')
    print_query_as_command('percentageCheckedProjects', 'SELECT COUNT(*) * 100.00 / (SELECT COUNT(*) FROM GithubProject) FROM GithubProjectCompletelyAnalyzed', percentage=True)
    print('% number of projects projects that use inline assembly')
    print_query_as_command('nrProjectsWithInlineAssembly', 'SELECT COUNT(*) FROM GithubProjectWithInlineAsm')
    print('% number of checked projects (i.e., excluding those where we did not analyze the single instruction sequences) that use inline assembly')
    print_query_as_command('nrCheckedProjectsWithInlineAssembly', 'SELECT COUNT(*) FROM GithubProjectWithCheckedInlineAsm')
    print('% percentage of projects that contain one or more inline assembly sequences')
    print_query_as_command('percentageProjectsWithInlineAsm', 'SELECT COUNT(*)*100.00 / (SELECT COUNT(*) FROM GithubProject) FROM GithubProjectWithInlineAsm', percentage=True)
    print('% percentage of checked projects of projects that have inline assembly sequences (checked + unchecked)')
    print_query_as_command('percentageCheckedProjectsWithInlineAsm', 'SELECT 100-COUNT(*)*100.00 / (SELECT COUNT(*) FROM GithubProjectWithInlineAsm) FROM GithubProjectNotCompletelyAnalyzed', percentage=True)
    print('% percentage of popular projects that use inline assembly')
    print_query_as_command('percentageProjectsWithInlineAssemblyByPopularity', 'SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM GithubProject WHERE GITHUB_NR_STARGAZERS >= ' + checked_down_to_stars +') FROM GithubProjectWithInlineAsm WHERE GITHUB_NR_STARGAZERS >= ' + checked_down_to_stars, percentage=True)
    print('% percentage of other projects that use inline assembly')
    print_query_as_command('percentageProjectsWithInlineAssemblyByOther', 'SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM GithubProject WHERE GITHUB_NR_STARGAZERS < ' + checked_down_to_stars +') FROM GithubProjectWithInlineAsm WHERE GITHUB_NR_STARGAZERS < ' + checked_down_to_stars, percentage=True)
    print('% average lines of code with the popularity gathering strategy')
    print_query_as_command('AverageKLinesCodeByPopularity', 'SELECT cast((SUM(CLOC_LOC_C)+SUM(CLOC_LOC_H) * 1.0) / (SELECT COUNT(*) FROM GithubProject WHERE GITHUB_NR_STARGAZERS >= ' + checked_down_to_stars + ') / 1000 as int) FROM GithubProjectWithInlineAsm WHERE GITHUB_NR_STARGAZERS >= ' + checked_down_to_stars)
    print('% average lines of code with the other gathering strategy')
    print_query_as_command('AverageKLinesCodeByOther', 'SELECT cast((SUM(CLOC_LOC_C)+SUM(CLOC_LOC_H) * 1.0) / (SELECT COUNT(*) FROM GithubProject WHERE GITHUB_NR_STARGAZERS < ' + checked_down_to_stars + ') / 1000 as int) FROM GithubProjectWithInlineAsm WHERE GITHUB_NR_STARGAZERS <' + checked_down_to_stars)

    print('\n%############ statistics about unchecked projects')
    print('% number of projects that we did not analyze because the contained too large/many inline assembly snippets (or we yet have to analyze)')
    print_query_as_command('numberProjectsNotAnalyzed', 'SELECT COUNT(*) FROM GithubProjectNotCompletelyAnalyzed')
    print('% percentage of all projects where we did NOT check the usage of inline assembly (but which contain inline assembly)')
    print_query_as_command('percentageProjectsNotAnalyzed', 'SELECT COUNT(*) * 100.00 / (SELECT COUNT(*) FROM GithubProject) FROM GithubProjectNotCompletelyAnalyzed', percentage=True)
    print('% percentage of unchecked projects that have inline assembly sequences (checked + unchecked)')
    print_query_as_command('percentageUncheckedProjectsWithInlineAsm', 'SELECT COUNT(*)*100.00 / (SELECT COUNT(*) FROM GithubProjectWithInlineAsm) FROM GithubProjectNotCompletelyAnalyzed', percentage=True)


    print('\n%############ statistics about inline assembly frequences')
    print('\n% average number of inline assembly snippets computed over the set of projects that use inline assembly')
    print_query_as_command('avgNrInlineAssemblySnippets', 'SELECT AVG(number) FROM (SELECT SUM(NR_OCCURRENCES) as number FROM AsmSequencesInAnalyzedGithubProjects GROUP BY GITHUB_PROJECT_ID);', roundn=True)
    print('% median number of inline assembly snippets computed over the set of projects that use inline assembly')
    print_query_as_command('medianNrInlineAssemblySnippets', 'SELECT SUM(NR_OCCURRENCES) as number FROM AsmSequencesInAnalyzedGithubProjects GROUP BY GITHUB_PROJECT_ID ORDER BY number LIMIT 1 OFFSET (SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) / 2 FROM AsmSequencesInAnalyzedGithubProjects)')
    print('% average number of unique inline assembly snippets computed over the set of projects that use inline assembly')
    print_query_as_command('avgNrUniqueInlineAssemblySnippets', 'SELECT AVG(number) FROM (SELECT COUNT(DISTINCT ASM_SEQUENCE_ID) as number FROM AsmSequencesInAnalyzedGithubProjects GROUP BY GITHUB_PROJECT_ID);', roundn=True)
    print('% total number of inline assembly snippets')
    print_query_as_command('nrInlineAssemblySnippets', 'SELECT SUM(NR_OCCURRENCES) FROM AsmSequencesInAnalyzedGithubProjects;')
    print('% total number of unique inline assembly snippets')
    print_query_as_command('nrUniqueInlineAssemblySnippets', 'SELECT COUNT(DISTINCT ASM_SEQUENCE_ID) FROM AsmSequencesInAnalyzedGithubProjects;')
    print('% total number of file-unique inline assembly snippets')
    print_query_as_command('nrFileUniqueInlineAssemblySnippets', 'SELECT COUNT(ASM_SEQUENCE_ID) FROM AsmSequencesInAnalyzedGithubProjects;')
    print('% average number of inline assembly snippets per instruction')
    print_query_as_command('avgNrInlineAssemblyInstructionsPerSnippet', 'SELECT AVG(number_instructions * NR_OCCURRENCES) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects;', roundn=True)
    print('% median number of inline assembly snippets per instruction')
    print_query_as_command('medianInlineAssemblyInstructionsPerSnippet', 'SELECT number_instructions * NR_OCCURRENCES as nr_instructions FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects ORDER BY nr_instructions LIMIT 1  OFFSET (SELECT (COUNT(*) - 1)  / 2 FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects)')
    print('% number of inline assembly snippets with one instruction')
    print_query_as_command('nrInlineAssemblySnippetsWithOnlyOneInstruction', 'SELECT SUM(NR_OCCURRENCES) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects WHERE number_instructions = 1')
    print('% percentage of inline assembly snippets with one instruction')
    print_query_as_command('percentageInlineAssemblySnippetsWithOnlyOneInstruction', 'SELECT 100.0 * SUM(NR_OCCURRENCES) / (SELECT SUM(NR_OCCURRENCES) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects WHERE number_instructions = 1', percentage=True)
    print('% percentage of inline assembly snippets with one or two instructions')
    print_query_as_command('percentageInlineAssemblySnippetsWithOnlyOneOrTwoInstruction', 'SELECT 100.0 * SUM(NR_OCCURRENCES) / (SELECT SUM(NR_OCCURRENCES) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects WHERE number_instructions <= 2', percentage=True)
    print('% percentage of inline assembly projects with only one unique inline assembly fragment')
    print_query_as_command('percentageInlineAssemblyProjectsWithOneUniqueFragment', 'SELECT COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) FROM AsmSequencesInAnalyzedGithubProjects) FROM (SELECT COUNT(ASM_SEQUENCE_ID) as nr_snippets FROM AsmSequencesInAnalyzedGithubProjects GROUP BY GITHUB_PROJECT_ID) WHERE nr_snippets = 1', percentage=True)
    print('% percentage of inline assembly projects with up to ten unique inline assembly fragments')
    print_query_as_command('percentageInlineAssemblyProjectsWithUpToTenUniqueFragments', 'SELECT COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) FROM AsmSequencesInAnalyzedGithubProjects) FROM (SELECT COUNT(ASM_SEQUENCE_ID) as nr_snippets FROM AsmSequencesInAnalyzedGithubProjects GROUP BY GITHUB_PROJECT_ID) WHERE nr_snippets <= 10', percentage=True)
    print('% inline assembly snippet with most instructions')
    print_query_as_command('nrInstructionsLargestInlineAssemblySnippet', 'SELECT MAX(number_instructions) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects')
    print('% maximum number of inline assembly snippets in a project')
    print_query_as_command('maxNrInlineAssemblySnippetsInProject', 'SELECT MAX(nr_snippets) FROM (SELECT SUM(NR_OCCURRENCES) as nr_snippets FROM AsmSequencesInAnalyzedGithubProjects GROUP BY GITHUB_PROJECT_ID)')


    print('\n%############ statistics about mnemonics')
    print('% total number of projects that contain non-mnemonic instructions')
    print_query_as_command('nrProjectsWithoutMnemonics', 'SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) FROM AsmSequencesInAnalyzedGithubProjects WHERE MNEMONIC = 0')
    print('% percentage of projects with inline assembly snippets that contain at least one non-mnemonic instruction')
    print_query_as_command('percentageInlineSnippetsWithoutMnemonics', 'SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) * 100.0 / (SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) FROM AsmSequencesInAnalyzedGithubProjects) FROM AsmSequencesInAnalyzedGithubProjects WHERE MNEMONIC = 0', percentage=True)
    print('% percentage of projects whose first commit was in 2008 or later')
    print_query_as_command('percentageProjectsAfterGithubLaunch', 'SELECT (SELECT COUNT(*) FROM GithubProject WHERE GIT_FIRST_COMMIT_DATE >= 2008) * 100.0 /  COUNT(*) FROM GithubProject', percentage=True)
    # SELECT AsmInstruction.ID, AsmInstruction.INSTRUCTION, (SELECT COUNT(DISTINCT AsmSequencesInGithubProject.Github_PROJECT_ID) FROM AsmSequenceInstruction, AsmSequencesInGithubProject WHERE AsmSequenceInstruction.ASM_INSTRUCTION_ID = AsmInstruction.ID AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID) FROM AsmInstruction;
    # SELECT * FROM AsmSequenceInstruction WHERE AsmSequenceInstruction.ASM_INSTRUCTION_ID = 9
    # SELECT COUNT(DISTINCT AsmSequencesInGithubProject.Github_PROJECT_ID) FROM AsmSequenceInstruction, AsmSequencesInGithubProject WHERE AsmSequenceInstruction.ASM_INSTRUCTION_ID = 7 AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID


    print('\n%########### statistics about instruction groups')
    query = "SELECT 100.0 * COUNT(DISTINCT AsmSequencesInAnalyzedGithubProjects.Github_PROJECT_ID) / (SELECT COUNT(*) FROM GithubProjectWithCheckedInlineAsm) FROM AsmSequencesInAnalyzedGithubProjects, AsmInstruction, AsmSequenceInstruction WHERE AsmSequencesInAnalyzedGithubProjects.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID AND AsmSequenceInstruction.ASM_INSTRUCTION_ID = AsmInstruction.ID AND (AsmInstruction.INSTRUCTION %s)"
    print_query_as_command('percentageProjectsWithControlFlowInstructions', query % 'LIKE "j%" OR AsmInstruction.INSTRUCTION IN ("cmp", "test")', percentage=True)
    print_query_as_command('percentageProjectsWithFenceInstructions', query % "IN ('mfence', 'lfence', 'sfence')", percentage=True)
    print_query_as_command('percentageBitScanInstructions', query % "IN ('bsr', 'bsf')", percentage=True)
    print_query_as_command('percentageHashInstructions', query % "IN ('rol', 'ror', 'shl', 'crc32')", percentage=True)
    print_query_as_command('percentageProjectsWithTimeInstructions', query % "IN ('cpuid', 'rdtsc', '')", percentage=True)
    print_query_as_command('percentageProjectsWithAtomicInstructions', query % "LIKE 'lock%'", percentage=True)
    print_query_as_command('percentageProjectsWithArithmeticInstructions', query % "IN ('xor', 'add', 'or', 'sub', 'and', 'inc', 'dec', 'mul', 'adc', 'dec', 'neg', 'lea')", percentage=True)
    print_query_as_command('percentageProjectsWithPauseInstructions', query % "LIKE 'pause'", percentage=True)
    print_query_as_command('percentageProjectsWithCompilerBarriers', query % "LIKE ''", percentage=True)
    print_query_as_command('percentageProjectsWithEndiannessInstructions', query % "IN ('lock xchg', 'rol', 'ror', 'bswap')", percentage=True)
    print_query_as_command('percentageProjectsWithPrefetch', query % "LIKE 'prefetch'", percentage=True)
    print_query_as_command('percentageProjectsWithRandomNumber', query % "LIKE 'rdrand'", percentage=True)
    print_query_as_command('percentageProjectsWithNop', query % "LIKE 'nop'", percentage=True)
    print_query_as_command('percentageProjectsWithSet', query % "LIKE 'set%'", percentage=True)
    print_query_as_command('percentageProjectsWithRep', query % "LIKE 'rep%' OR AsmInstruction.INSTRUCTION like 'cld'", percentage=True)
    print_query_as_command('percentageProjectsWithFeatureDetection', query % "IN ('cpuid', 'xgetbv')", percentage=True)
    print_query_as_command('percentageProjectsWithAES', query % "IN ('aesdec', 'aesdeclast', 'aesenc', 'aesenclast', 'aesimc', 'aeskeygena')", percentage=True)
    print_query_as_command('percentageProjectsWithDebugInterrupt', query % "IS 'int $0x03'", percentage=True)
    print_query_as_command('percentageProjectsWithSIMD', query % "IN ('pxor', 'movdqa', 'movdqu', 'psrlq', 'pclmulqdq', 'pshufd', 'pslldq', 'pslldq', 'psllq', 'psrldq')", percentage=True)
    print_query_as_command('percentageProjectsWithMoves', query % "IN ('mov', 'push', 'pop', 'pushf', 'popf')", percentage=True)


    print('\n%########## statistics about macro assembly')
    print('% total number of projects that contain macro assembler instructions')
    print_query_as_command('nrProjectsWithMacroAssembly', 'SELECT COUNT(*) FROM GithubProject WHERE CLOC_LOC_ASSEMBLY > 0')
    print('% percentage of projects with macro assembler instructions (projects with .S files)')
    print_query_as_command('percentageProjectsWithMacroAssembly', 'SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) From GithubProject) FROM GithubProject WHERE CLOC_LOC_ASSEMBLY > 0', percentage=True)
    print('% avg number of macro assembly LOC in projects that use macro assembly')
    print_query_as_command('avgLocMacroAssembly', 'SELECT SUM(CLOC_LOC_ASSEMBLY) * 1.0 / (SELECT COUNT(*) From GithubProject) FROM GithubProject WHERE CLOC_LOC_ASSEMBLY > 0', roundn=True)
    print('% percentage of projects with inline assembler that also contain macro assembler instructions')
    print_query_as_command('percentageProjectsWithMacroAssemblyInlineAssemblyProjects', 'SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) From GithubProjectWithInlineAsm) FROM GithubProjectWithInlineAsm WHERE CLOC_LOC_ASSEMBLY > 0', percentage=True)
    
    print('\n%########## implementation')
    query = 'SELECT 100-COUNT(DISTINCT GITHUB_PROJECT_ID) * 100.0 / (SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) FROM AsmInstructionsInAnalyzedGithubProjects) FROM AsmInstructionsInAnalyzedGithubProjects WHERE INSTRUCTION NOT IN (%s)'
    def make_list(name):
        print('%', (','.join('"' + instr + '"' for instr in instructions)))
        q = query % (','.join('"' + instr + '"' for instr in instructions))
        print_query_as_command(name, q, percentage=True)
    instructions = ()
    make_list('percentageNoInstructionImplemented')
    instructions = instructions + ('rdtsc', 'rdtscp')
    make_list('percentageTimeInstructionsImplemented')
    instructions = instructions + ('cpuid', 'xgetbv')
    make_list('percentageFeatureInstructionsImplemented')
    instructions = instructions + ('', 'prefetch', 'nop', 'int $0x03', 'pause', 'mfence', 'sfence', 'lfence')
    make_list('percentageBarrierInstructionsImplemented')
    instructions = instructions + ('bsr', 'bsf', 'or', 'xor', 'neg', 'bswap', 'shl', 'rol', 'ror')
    make_list('percentageByteManipulationInstructionsImplemented')
    instructions = instructions + ('lock xchg', 'lock cmpxchg', 'lock xadd', 'lock add')#('lock xchg', 'lock cmpxchg', 'lock xadd', 'lock add', 'lock dec', 'lock inc', 'lock xor', 'lock neg', 'lock btc', 'lock btr')
    make_list('percentageLockInstructionsImplemented')
    instructions = instructions + ('mov', 'push', 'pop')
    make_list('percentageMovInstructionsImplemented')
    instructions = instructions + ('crc32',)
    make_list('percentageCrcInstructionsImplemented')
    instructions = instructions + ('sete', 'setz', 'setc')
    make_list('percentageSetInstructionsImplemented')
    instructions = instructions + ('add', 'sub', 'mul', 'adc', 'lea', 'inc', 'dec', 'div', 'imul', 'sbb')
    make_list('percentageArithmeticInstructionsImplemented')
    instructions = instructions + ('rdrand',)
    make_list('rdrandInstructionsImplemented')
    instructions = instructions + ('jmp', 'jnc') #%, 'test', 'jz', 'jnz', 'jl', 'ja', 'jbe', 'je', 'jne', 'jb', 'jnc')
    make_list('percentageControlFlowInstructionsImplemented')
    instructions = instructions + ('rep movs', )
    make_list('percentageStringInstructionsImplemented')
    print_query_as_command('nrImplementedInstructions', 'SELECT ' + str(len(instructions)))
    print_query_as_command('percentageImplementedTotal', 'SELECT 100-(SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) + (SELECT COUNT(*) FROM GithubProjectNotCompletelyAnalyzed) FROM AsmInstructionsInAnalyzedGithubProjects WHERE INSTRUCTION NOT IN (%s)) * 100.0 / COUNT(*) FROM GithubProjectWithInlineAsm' % (','.join('"' + instr + '"' for instr in instructions)), percentage=True)

    sys.stdout.close()
    # SELECT INSTRUCTION, COUNT(GITHUB_PROJECT_ID) as count FROM AsmInstructionsInAnalyzedGithubProjects WHERE GITHUB_PROJECT_ID IN (SELECT GITHUB_PROJECT_ID FROM AsmInstructionsInAnalyzedGithubProjects WHERE INSTRUCTION NOT IN ('rdtsc', 'rdtscp', 'cpuid', 'xgetbv', '', 'prefetch', 'nop', 'int $0x03', 'pause', 'mfence', 'sfence', 'lfence', 'bsr', 'bsf', 'or', 'and', 'xor', 'neg', 'bswap', 'shl', 'rol', 'ror', 'shr', 'lock xchg', 'lock cmpxchg', 'lock xadd', 'crc32', 'mov') GROUP BY GITHUB_PROJECT_ID HAVING COUNT(ASM_INSTRUCTION_ID) =1) GROUP BY INSTRUCTION ORDER BY count DESC

    # number of non-unique snippets per project (TODO: does not completely round up to 100%)
    sys.stdout = open(output_dir + '/nr_snippets.csv', 'w+')
    print('nr_unique_snippets;percentage')
    max_nr_snippets = c.execute('SELECT MAX(nr_snippets) FROM (SELECT SUM(NR_OCCURRENCES) as nr_snippets FROM AsmSequencesInAnalyzedGithubProjects GROUP BY GITHUB_PROJECT_ID)').fetchone()[0]
    for nr_snippets in range(1, max_nr_snippets+1):
        nr_occurrences = c.execute('SELECT COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT GITHUB_PROJECT_ID) FROM AsmSequencesInAnalyzedGithubProjects) FROM (SELECT COUNT(ASM_SEQUENCE_ID) as nr_snippets FROM AsmSequencesInAnalyzedGithubProjects GROUP BY GITHUB_PROJECT_ID) WHERE nr_snippets <= ?;', (nr_snippets,)).fetchone()[0]
        print(str(nr_snippets) + ';' + str(nr_occurrences))
    sys.stdout.close()

    # instruction length per snippet
    sys.stdout = open(output_dir + '/instruction_lengths.csv', 'w+')
    print('nr_instructions;percentage')
    max_instructions_per_snippet = c.execute('SELECT MAX(number_instructions) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects').fetchone()[0]
    for nr_instructions in range(1, max_instructions_per_snippet+1):
        nr_occurrences = c.execute('SELECT SUM(NR_OCCURRENCES)*100.0 / (SELECT SUM(NR_OCCURRENCES) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects) FROM AsmSequencesWithInstructionCountsInAnalyzedGithubProjects WHERE number_instructions <= ?', (nr_instructions,)).fetchone()[0]
        print(str(nr_instructions) + ';' + str(nr_occurrences))
    sys.stdout.close()


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
        query = """insert into GithubProjectUnfiltered(
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
    if args.file is None:
        print("specify --file arg to specify the output directory")
        exit(-1)
    database_integrity_tests()
    show_stats(args.file)

