import sqlite3
import argparse


parser = argparse.ArgumentParser(description='Manipulate the inline assembler database.')

parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['categories'])
parser.add_argument('database', metavar='DATABASE', help="path to the sqlite3 database")
args = parser.parse_args()

print args.database
conn = sqlite3.connect(args.database)
c = conn.cursor()


def print_sub_cat(super_id, tabs="\t"):
   """ display sub categories of a certain id. """
   for row in c.execute('select * from ApplicationCategory where SUPER_ID =?;', (str(super_id),)).fetchall():
      print tabs + row[1]
      print_sub_cat(tabs + '\t', row[0])

def display_application_cats():
    """ Recursively displays all application categories. """
    rows = c.execute('select * from ApplicationCategory where SUPER_ID IS NULL;')
    for row in rows.fetchall():
        super_cat = row[1]
        print(super_cat)
        print_sub_cat(row[0])



FUNCTION_MAP = {'categories' : display_application_cats,
}

func = FUNCTION_MAP[args.command]
func()
