import hashlib, json, tarfile, sys
from pathlib import Path
for manifest in Path('.').glob('*/MMX2/app/70/default/app_extracted_manifest.json'):
    if len(sys.argv) > 1 and sys.argv[1] not in str(manifest):
        continue
    root = manifest.parent / 'app_extracted'
    records = json.loads(manifest.read_text(encoding='utf-8'))
    count = total = 0
    for record in records:
        if 'sha256' not in record:
            continue
        path = root / record['path']
        assert path.stat().st_size == record['size'], path
        with path.open('rb') as f:
            assert hashlib.file_digest(f, 'sha256').hexdigest() == record['sha256'], path
        count += 1
        total += record['size']
    print(manifest.parts[0], count, 'files verified', total, 'bytes', flush=True)
    archive = manifest.parent / 'app_extracted.tar'
    with tarfile.open(archive, 'x') as tar:
        for record in records:
            info = tarfile.TarInfo(record['path'])
            info.mode = int(record['mode'], 8) & 0o7777
            info.uid, info.gid, info.mtime = record['uid'], record['gid'], record['mtime']
            if 'sha256' in record:
                info.size = record['size']
                with (root / record['path']).open('rb') as f:
                    tar.addfile(info, f)
            elif 'symlink_target' in record:
                info.type = tarfile.SYMTYPE
                info.linkname = record['symlink_target']
                tar.addfile(info)
            elif stat_isdir := (int(record['mode'], 8) & 0o170000) == 0o040000:
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            else:
                raise ValueError(record)
    print(archive, 'created with original symlinks and permissions', flush=True)
