"""Read the physical cluster terminal from a dmdt gs report.

No guessing from fallback values, photographs or the central PCM screen.
"""
import argparse
import json
from pathlib import Path
import re


def read_cluster(text, terminal='2nd_lvds'):
    if 'displaymanager reports the following system information:' not in text:
        raise ValueError('Incomplete dmdt system-information response')
    blocks = re.split(r'^display\s+(\d+):\s*$', text, flags=re.MULTILINE)
    found = []
    for index in range(1, len(blocks), 2):
        metadata = re.findall(r'^\s*terminal:\s*(\S+)\s*$', blocks[index + 1], re.MULTILINE)
        if metadata != [terminal]:
            continue
        sizes = re.findall(r'^\s*size:\s*(\d+)\s*x\s*(\d+)\s*$', blocks[index + 1], re.MULTILINE)
        contexts = re.findall(r'^\s*context id:\s*(-?\d+)\s*$', blocks[index + 1], re.MULTILINE)
        if len(sizes) != 1 or len(contexts) != 1:
            raise ValueError('Ambiguous or incomplete cluster display block')
        width, height = map(int, sizes[0])
        if not (64 <= width <= 8192 and 64 <= height <= 8192):
            raise ValueError('Invalid cluster dimensions')
        found.append({'report_display_index': int(blocks[index]), 'terminal': terminal,
                      'width': width, 'height': height,
                      'context_id': int(contexts[0]), 'source': 'dmdt gs runtime response',
                      'carplay_output_proven': False})
    if len(found) != 1:
            raise ValueError('Expected exactly one named cluster terminal; central display is not a fallback')
    return found[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('system_report', type=Path)
    args = parser.parse_args()
    try:
        result = read_cluster(args.system_report.read_text(encoding='utf-8'))
    except ValueError as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))
