#!/usr/bin/python

# This was inspired by
# http://sigs.k8s.io/contributor-site/hack/gen-content.sh

import csv
import os
import re
import shutil
import sys
import subprocess
import tempfile

# Workaround to make this work in Netlify...
local_py_path = '/opt/buildhome/python3.7/lib/python3.7/site-packages/'
if local_py_path not in sys.path:
    sys.path.append(local_py_path)

import pathlib

global link_mapping
link_mapping = []

'''
We are adding basic Front-Matter here.

`docs` files can't have front-matter and # (h1)
'''
def rewrite_header(out_file, title=None, docs=False):
    lines = open(out_file, 'r').readlines()

    if not title:
        title = os.path.basename(out_file).split('.md')[0].title()
    header_lines = [
        '---\n',
        'title: {}\n'.format(title),
        'importedDoc: true\n',
        '---\n',
        '\n'
    ]

    f = open(out_file, 'w')
    f.writelines(header_lines)

    for line in lines:
        if not docs or not line.startswith('# ') or lines.index(line) >= 4:
            f.write(line)
    f.close()

class Repo():
    def __init__(self, external_sources_dir, repo_fn):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_id = repo_fn.split(external_sources_dir)[1][1:]
        self.gh_source = 'https://github.com/{}/'.format(self.repo_id).strip('/')
        self.repo_fn = repo_fn
        self.dest = os.path.join(self.temp_dir, self.repo_id)
        self.file_list = []

        global link_mapping
        with open(self.repo_fn, 'r') as f:
            csv_reader = csv.reader(f)
            for line in csv_reader:
                self.file_list += [[entry.strip('/') for entry in line]]
                link_mapping += [[entry.strip('/') for entry in line]]

    def __del__(self):
        shutil.rmtree(self.temp_dir)

    def clone_repo(self):
        subprocess.call(['git', 'clone', '--depth=1', '-q',
            self.gh_source, self.dest])

    def rewrite_links(self, out_file):
        content = open(out_file, 'r').read()
        for link in re.findall(r'\[.+?\]\((.+?)\)', content, re.MULTILINE):
            link = link.split('#')[0]
            if not link:
                continue
            global link_mapping
            for entry in link_mapping:
                if link == entry[0]:
                    content = content.replace(
                        link, '/{}'.format(entry[1].lower().split('.md')[0]))
                elif link.startswith(self.gh_source) and link.endswith(entry[0]):
                    content = content.replace(
                        link,  '/{}'.format(entry[1].lower().split('.md')[0]))
            if not link.startswith('https://'):
                content = content.replace(
                    link, '{}/blob/main/{}'.format(self.gh_source, link))
        f = open(out_file, 'w')
        f.write(content)
        f.close()

    def copy_files(self, content_dir):
        for entry in self.file_list:
            out_file = os.path.join(content_dir, entry[1])
            shutil.copyfile(
                os.path.join(self.dest, entry[0]),
                out_file)
            docs = entry[1].startswith('docs/')
            if len(entry) == 3:
                rewrite_header(out_file, title=entry[2], docs=docs)
            else:
                rewrite_header(out_file, docs=docs)
            self.rewrite_links(out_file)


def get_repo_list(external_sources_dir):
    repos = []
    file_refs = pathlib.Path(external_sources_dir).glob('*/*')
    for file in file_refs:
        repo_fn = str(file)
        if os.path.isfile(repo_fn):
            repos += [Repo(external_sources_dir, repo_fn)]
    return repos


def main():
    repo_root = os.path.realpath(
        os.path.join(os.path.dirname(__file__), '..'))

    if os.getcwd() != repo_root:
        print('Please run this script from top-level of the repository.')
        sys.exit(1)

    content_dir = os.path.join(repo_root, 'content/en')
    external_sources_dir = os.path.join(repo_root, 'external-sources')

    repos = get_repo_list(external_sources_dir)
    for repo in repos:
        repo.clone_repo()
    for repo in repos:
        repo.copy_files(content_dir)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted.", sys.stderr)
        sys.exit(1)
