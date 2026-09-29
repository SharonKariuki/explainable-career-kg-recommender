"""Download O*NET 31.0, ESCO v1.1.0 and the ESCO-O*NET crosswalk into data/raw/.

Files already on disk with the expected checksum are left alone, so the
command is safe to re-run.
"""

import hashlib
import sys
import urllib.request
import zipfile

from pipeline import RAW_DIR

SOURCES = [
    {
        'name': 'O*NET 31.0 text database',
        'url': 'https://www.onetcenter.org/dl_files/database/db_31_0_text.zip',
        'path': RAW_DIR / 'onet' / 'db_31_0_text.zip',
        'sha256': '6883548adf5fde64cf6f801b35d15519c9225f2732c3cab0e281c652d16b23a9',
        'extract_to': RAW_DIR / 'onet',
        'extracted': RAW_DIR / 'onet' / 'db_31_0_text',
    },
    {
        'name': 'ESCO v1.1.0 classification (English, CSV)',
        'url': 'https://ec.europa.eu/esco/download/ESCO%20dataset%20-%20v1.1.0%20-%20classification%20-%20en%20-%20csv.zip',
        'path': RAW_DIR / 'esco' / 'ESCO_dataset_v1.1.0_classification_en_csv.zip',
        'sha256': '3b2ed440310d85edda9594773abbf113246eb11d07de83393879b3f167e5e45a',
        'extract_to': RAW_DIR / 'esco' / 'ESCO_v1.1.0',
        'extracted': RAW_DIR / 'esco' / 'ESCO_v1.1.0',
    },
    {
        'name': 'ESCO-O*NET crosswalk',
        'url': 'https://esco.ec.europa.eu/system/files/2023-08/ONET_%28Occupations%29_0_updated.csv',
        'path': RAW_DIR / 'esco' / 'ONET_Occupations_0_updated.csv',
        'sha256': '82179a0a3340da97b63df90134d8d941ec3c2c478334d855b69e4dd57a91b620',
    },
]


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(source):
    path = source['path']
    if path.exists() and sha256_of(path) == source['sha256']:
        print(f"ok        {source['name']}")
    else:
        print(f"download  {source['name']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(source['url'], path)
        actual = sha256_of(path)
        if actual != source['sha256']:
            sys.exit(f"Checksum mismatch for {path.name}: expected {source['sha256']}, got {actual}")

    if 'extract_to' in source and not source['extracted'].exists():
        print(f"extract   {path.name}")
        with zipfile.ZipFile(path) as archive:
            archive.extractall(source['extract_to'])


def main():
    for source in SOURCES:
        fetch(source)


if __name__ == '__main__':
    main()
