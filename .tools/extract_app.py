import sys, stat, json, hashlib, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'qnxmount'))
from qnxmount.stream import Stream
from qnxmount.qnx6.interface import QNX6FS

for image in Path('.').glob('*/MMX2/app/70/default/app.img'):
    out = image.parent / 'app_extracted'
    out.mkdir(exist_ok=False)
    records = []
    with Stream(image) as stream:
        fs = QNX6FS(stream)
        def walk(ino, rel, ancestors):
            node = fs.get_inode(ino)
            dest = out / rel
            record = dict(path=rel.as_posix(), inode=ino, mode=oct(node.mode), uid=node.uid, gid=node.gid, mtime=node.mtime, size=node.size)
            records.append(record)
            if stat.S_ISDIR(node.mode):
                if ino in ancestors:
                    raise ValueError('Directory cycle')
                dest.mkdir(exist_ok=True)
                for entry in fs.get_dir(ino).entries:
                    name = entry.content.name
                    if name in ('.', '..'):
                        continue
                    if '/' in name or '\\' in name or ':' in name or not name:
                        raise ValueError(f'Unsafe filename: {name!r}')
                    walk(entry.inode_number, rel / name, ancestors | {ino})
            elif stat.S_ISREG(node.mode):
                digest = hashlib.sha256()
                with dest.open('xb') as f:
                    for offset in range(0, node.size, 1024 * 1024):
                        data = fs.read_file(node, offset, min(1024 * 1024, node.size - offset))
                        f.write(data)
                        digest.update(data)
                assert dest.stat().st_size == node.size
                record['sha256'] = digest.hexdigest()
                os.utime(dest, (node.mtime, node.mtime))
            elif stat.S_ISLNK(node.mode):
                record['symlink_target'] = fs.read_file(node).decode('utf-8', errors='surrogateescape')
            else:
                record['special_file'] = True
        walk(1, Path('.'), set())
    manifest = image.parent / 'app_extracted_manifest.json'
    manifest.write_text(json.dumps(records, indent=2, ensure_ascii=True), encoding='utf-8')
    print(image, 'DONE', len(records), 'entries', sum('sha256' in r for r in records), 'files', sum('symlink_target' in r for r in records), 'symlinks (in manifest)', flush=True)
