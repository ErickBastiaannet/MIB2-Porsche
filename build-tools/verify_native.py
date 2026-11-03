"""Verify the exact MU1417 AirPlay security layout using its ARM instructions.

Only synthetic session keys are used. No firmware is changed or distributed.
"""
import argparse
import hashlib
import io
import json
import struct
import sys
from pathlib import Path

AIRPLAY_SHA256 = '816f1fa8b333ca091676cea65d405f36adb82ceee5119eb6f8f99538678b527a'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library', type=Path)
    parser.add_argument('--deps', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.library.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != AIRPLAY_SHA256:
        raise SystemExit('Unrecognised AirPlay library; layout verification refused')
    if args.deps:
        sys.path.insert(0, str(args.deps.resolve()))
    from elftools.elf.elffile import ELFFile
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP

    elf = ELFFile(io.BytesIO(raw))
    if elf['e_machine'] != 'EM_ARM' or not elf.little_endian:
        raise SystemExit('Unexpected architecture')
    symbols = {s.name: s for s in elf.get_section_by_name('.dynsym').iter_symbols()}
    symbol = symbols['AirPlayReceiverSessionSetSecurityInfo']
    section = elf.get_section(symbol['st_shndx'])
    start = symbol['st_value'] - section['sh_addr']
    code = section.data()[start:start + symbol['st_size']]
    # Resolve ARM PLT entries through relocations, rather than labelling calls
    # from a guessed import order. The function itself is never rewritten.
    plt = elf.get_section_by_name('.plt')
    relocations = elf.get_section_by_name('.rel.plt')
    dynsym = elf.get_section(relocations['sh_link'])
    imports = {plt['sh_addr'] + 20 + i * 12: dynsym.get_symbol(r['r_info_sym']).name
               for i, r in enumerate(relocations.iter_relocations())}
    base, session, key, iv, stack, stop = 0x10000000, 0x20000000, 0x21000000, 0x21001000, 0x22000000, 0x23000000
    synthetic_key, synthetic_iv = bytes(range(16)), bytes(range(128, 144))
    results = []
    for init_result in [0, 7]:
        emulator = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        image_size = (max(s['p_vaddr'] + s['p_memsz'] for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD') + 4095) & ~4095
        emulator.mem_map(base, image_size)
        for segment in elf.iter_segments():
            if segment['p_type'] == 'PT_LOAD':
                emulator.mem_write(base + segment['p_vaddr'], segment.data())
        for address, size in [(session, 4096), (key, 8192), (stack, 65536), (stop, 4096)]:
            emulator.mem_map(address, size)
        emulator.mem_write(session, b'\xa5' * 4096)
        emulator.mem_write(key, synthetic_key)
        emulator.mem_write(iv, synthetic_iv)
        calls = []

        def hook(machine, address, size, user):
            if address == stop:
                machine.emu_stop()
                return
            name = imports.get(address - base)
            if not name:
                return
            calls.append(name)
            if name == 'memcpy':
                destination = machine.reg_read(UC_ARM_REG_R0)
                source = machine.reg_read(UC_ARM_REG_R1)
                length = machine.reg_read(UC_ARM_REG_R2)
                assert length == 16
                machine.mem_write(destination, bytes(machine.mem_read(source, length)))
            elif name == 'AES_CBCFrame_Init':
                assert machine.reg_read(UC_ARM_REG_R1) == key
                assert machine.reg_read(UC_ARM_REG_R2) == iv
                machine.reg_write(UC_ARM_REG_R0, init_result)
            elif name != 'AES_CBCFrame_Final':
                raise AssertionError('Unexpected call: ' + name)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        emulator.hook_add(UC_HOOK_CODE, hook)
        for register, value in [(UC_ARM_REG_R0, session), (UC_ARM_REG_R1, key), (UC_ARM_REG_R2, iv),
                                (UC_ARM_REG_SP, stack + 65520), (UC_ARM_REG_LR, stop)]:
            emulator.reg_write(register, value)
        emulator.emu_start(base + symbol['st_value'], stop + 4, count=10000)
        assert emulator.reg_read(UC_ARM_REG_PC) == stop
        assert emulator.reg_read(UC_ARM_REG_R0) == init_result
        security = struct.unpack('<I', emulator.mem_read(session + 0x1c4, 4))[0]
        if init_result == 0:
            assert bytes(emulator.mem_read(session + 0x1c8, 16)) == synthetic_key
            assert bytes(emulator.mem_read(session + 0x1d8, 16)) == synthetic_iv
            assert security == session + 0xbc
            assert calls == ['AES_CBCFrame_Final', 'AES_CBCFrame_Init', 'memcpy', 'memcpy']
        else:
            assert bytes(emulator.mem_read(session + 0x1c8, 32)) == b'\xa5' * 32
            assert security == 0
            assert calls == ['AES_CBCFrame_Final', 'AES_CBCFrame_Init']
        results.append({'aes_init_status': init_result, 'calls_verified': calls})
    report = {
        'firmware': 'MHI2_ER_POG24_K5137_MU1417_971919360T',
        'library_sha256': digest, 'function_sha256': hashlib.sha256(code).hexdigest(),
        'session_key_offset': 0x1c8, 'session_iv_offset': 0x1d8,
        'security_ready_pointer_offset': 0x1c4,
        'verification': 'Original ARM function executed under Unicorn with synthetic inputs; external AES/memcpy calls stubbed',
        'cases': results, 'physical_unit_tested': False,
    }
    fingerprint = 2166136261
    for byte in code:
        fingerprint = ((fingerprint ^ byte) * 16777619) & 0xffffffff
    report['function_bytes'] = len(code)
    report['function_fnv1a'] = fingerprint
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('PORSCHE_NATIVE_SECURITY_PASS success/failure paths, key/IV offsets verified on exact ARM function')


if __name__ == '__main__':
    main()
