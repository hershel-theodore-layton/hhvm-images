#!/usr/bin/env python3
"""Copy versioned HHVM images once, preserving their manifests and platforms."""
import argparse
import hashlib
import json
import re
import subprocess

SOURCE = 'docker.io/hersheltheodorelayton'
DESTINATION = 'ghcr.io/hershel-theodore-layton/hhvm-images'
REPOSITORIES = ('hhvm-full', 'hhvm-basic')


def versioned(tag):
    match = re.fullmatch(r'(\d+)\.\d+\.\d+', tag)
    return match is not None and int(match[1]) > 6


def run(*args):
    return subprocess.run(['skopeo', *args], check=True, capture_output=True).stdout


def exists(image):
    try:
        run('inspect', '--raw', 'docker://' + image)
        return True
    except subprocess.CalledProcessError as error:
        message = error.stderr.decode(errors='replace')
        # Authentication and network errors must never be treated as cache misses.
        if re.search(r'\b(manifest unknown|name unknown)\b', message, re.IGNORECASE):
            return False
        raise


def mirror(source, destination):
    if exists(destination):
        print('Cached: ' + destination, flush=True)
        return
    manifest = run('inspect', '--raw', 'docker://' + source)
    digest = 'sha256:' + hashlib.sha256(manifest).hexdigest()
    pinned = source.rsplit(':', 1)[0] + '@' + digest
    run('copy', '--all', '--preserve-digests', '--retry-times', '3',
        'docker://' + pinned, 'docker://' + destination)
    copied = run('inspect', '--raw', 'docker://' + destination)
    if hashlib.sha256(copied).hexdigest() != digest.split(':')[1]:
        raise RuntimeError('Manifest digest mismatch: ' + destination)
    print('Copied: ' + destination + ' (' + digest + ')', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='List eligible images without pulling or publishing them.')
    args = parser.parse_args()
    for repository in REPOSITORIES:
        tags = json.loads(run('list-tags', 'docker://' + SOURCE + '/' + repository))['Tags']
        for tag in sorted(filter(versioned, tags)):
            source = SOURCE + '/' + repository + ':' + tag
            destination = DESTINATION + '/' + repository + ':' + tag
            if args.dry_run:
                print(source + ' -> ' + destination)
            else:
                mirror(source, destination)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.decode(errors='replace')) from error
