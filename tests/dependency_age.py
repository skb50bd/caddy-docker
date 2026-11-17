"""Check release provenance and every linked Go dependency against a minimum age."""
import concurrent.futures
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request


def check_module(module):
    name, version = module
    escaped = ''.join('!' + c.lower() if c.isupper() else c for c in name)
    url = f'https://proxy.golang.org/{escaped}/@v/{version}.info'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                info = json.load(response)
            break
        except (OSError, urllib.error.URLError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code < 500 and error.code != 429:
                raise
            if attempt == 2:
                raise
            time.sleep(0.5 * (2 ** attempt))
    return {'module': name, 'version': version, 'date': info['Time'], 'source': url}


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=7)
    info = subprocess.check_output(['docker', 'run', '--rm', '--entrypoint', 'caddy',
                                    sys.argv[1], 'build-info'], text=True)
    modules = []
    for line in info.splitlines():
        fields = line.split()
        if fields and fields[0] == 'dep':
            modules.append((fields[1], fields[2]))
    assert modules, 'No embedded module information'
    releases = json.loads((Path(__file__).parent.parent / 'dependency-releases.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        records = list(pool.map(check_module, modules))
    records += releases
    failures = [r for r in records if datetime.datetime.fromisoformat(
        r['date'].replace('Z', '+00:00')) > cutoff]
    print(json.dumps({'checked_at': now.isoformat(), 'cutoff': cutoff.isoformat(),
                      'records': records, 'failures': failures}, indent=2))
    if failures:
        raise SystemExit('FAIL: dependencies younger than seven days')
    print(f'PASS: {len(modules)} linked Go modules and {len(releases)} release/image dates are at least seven days old')


if __name__ == '__main__':
    main()
