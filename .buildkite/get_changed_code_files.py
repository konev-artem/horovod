import json
import logging
import os
import sys
import re

import requests

# this script outputs all code files that have changed between commit and base
# base is either the pull requests' base, or master if no pull request exists
# environment variable BUILDKITE_COMMIT provides the commit SHA
# environment variable BUILDKITE_PULL_REQUEST provides the pull request number
# environment variable BUILDKITE_PIPELINE_DEFAULT_BRANCH provides the default branch (master)

# files that match any of these regexps are considered non-code files
# even though those files have changed, they will not be in the output of this script
non_code_file_patterns = [
    r'^.buildkite/get_changed_code_files.py$',
    r'^.github/',
    r'^docs/',
    r'^.*\.md',
    r'^.*\.rst'
]


def get_pr_files(commit, pr_number):
    if not commit or not pr_number:
        return []

    response = requests.get(
        'https://api.github.com/repos/horovod/horovod/pulls/{pr_number}/commits'.format(
            pr_number=pr_number
        )
    )
    if response.status_code != 200:
        logging.error('Request failed: {}'.format(json.loads(response.text).get('message')))
        return []

    pr_commits_json = response.text
    pr_commits = json.loads(pr_commits_json)
    base_commit = pr_commits[0].get('parents')[0].get('sha')

    response = requests.get(
        'https://api.github.com/repos/horovod/horovod/compare/{base_commit}...{head_commit}'.format(
            base_commit=base_commit, head_commit=commit
        )
    )
    if response.status_code != 200:
        logging.error('Request failed: {}'.format(json.loads(response.text).get('message')))
        return []

    compare_json = response.text
    compare = json.loads(compare_json)
    return [file.get('filename') for file in compare.get('files')]


def get_changed_files(base, head):
    response = requests.get(
        'https://api.github.com/repos/horovod/horovod/compare/{base}...{head}'.format(
            base=base, head=head
        )
    )
    if response.status_code != 200:
        logging.error('Request failed: {}'.format(json.loads(response.text).get('message')))
        return []

    compare_json = response.text
    compare = json.loads(compare_json)
    return [file.get('filename') for file in compare.get('files')]


def is_code_file(file):
    return not is_non_code_file(file)


def is_non_code_file(file):
    return any([pattern
                for pattern in non_code_file_patterns
                if re.match(pattern, file)])


if __name__ == "__main__":
    logging.getLogger().level = logging.DEBUG

    commit = os.environ.get('BUILDKITE_COMMIT')
    pr_number = os.environ.get('BUILDKITE_PULL_REQUEST')
    logging.debug('commit = {}'.format(commit))
    logging.debug('pr number = {}'.format(pr_number))

    commit_files = []
    if pr_number is not None and pr_number != 'false':
        commit_files = get_pr_files(commit, int(pr_number))
    else:
        default = os.environ.get('BUILDKITE_PIPELINE_DEFAULT_BRANCH')
        logging.debug('default = {}'.format(default))
        if default:
            commit_files = get_changed_files(default, commit)

    if len(commit_files) == 0:
        logging.warning('could not find any commit files')
        sys.exit(1)

    changed_code_files = [file
                          for file in commit_files
                          if is_code_file(file)]
    for file in changed_code_files:
        print(file)
