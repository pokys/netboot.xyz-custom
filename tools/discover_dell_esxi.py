"""Find published ESXi ISO links in Dell's public product indexes.

Writes candidates and a coverage report to an ignored research directory.
It never changes the reviewed catalog or menu. Dell Support pages for newer
versions still need separate review; many publish release notes only.
"""
import argparse
import concurrent.futures
import datetime
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = 'https://downloads.dell.com/published/Pages/'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))


def fetch_links(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        parser = Links()
        parser.feed(response.read().decode('utf-8', errors='replace'))
        return parser.links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.build/dell-discovery'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pages = sorted(set(name for name in fetch_links(BASE + 'index.html') if re.fullmatch(
        r'(?:poweredge-(?:[rcmtfx]\d|blade|sc\d).*|oemr-.*|vmware-esxi.*|vmware-esx-.*|vmware-vsphere.*|vmware-vsan.*)\.html', name, re.I)))

    def scan(name):
        url = BASE + name
        try:
            found = []
            for link in fetch_links(url):
                candidate = urllib.parse.urlsplit(urllib.parse.urljoin(url, link))
                if candidate.hostname not in ('downloads.dell.com', 'dl.dell.com'):
                    continue
                if not re.search(r'(?:vmvisor|esxi).*\.iso$', candidate.path, re.I):
                    continue
                path = urllib.parse.quote(urllib.parse.unquote(candidate.path), safe='/._-')
                found.append(urllib.parse.urlunsplit(('https', candidate.netloc, path, '', '')))
            return url, sorted(set(found)), None
        except (OSError, ValueError) as exc:
            return url, [], str(exc)

    images = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for number, (source, urls, error) in enumerate(pool.map(scan, pages), 1):
            if error:
                failures.append({'source': source, 'error': error})
            for url in urls:
                images.setdefault(url, []).append(source)
            if number % 20 == 0:
                print(f'{number}/{len(pages)} pages; {len(images)} ISO candidates', flush=True)
    report = {'date': datetime.date.today().isoformat(), 'index': BASE + 'index.html',
              'pages': pages, 'failures': failures, 'images': images}
    output = args.output / 'dell-candidates.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'{len(images)} ISO candidates; {len(failures)} failed pages. Saved {output}')


if __name__ == '__main__':
    main()
