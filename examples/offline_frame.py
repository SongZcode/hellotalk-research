"""Exercise the existing frame module with synthetic local data only."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ht_frame


def main():
    payload = {'example': 'offline', 'url': 'https://example.invalid/demo'}
    opcode = ht_frame.build_opcode(ht_frame.OP['presence'], 1, ht_frame.MARKER['presence'])
    for compressed in (True, False):
        frame = ht_frame.pack_json(opcode, 0, payload, compress=compressed)
        parsed = ht_frame.parse(frame)
        if parsed.get('body') != payload:
            raise RuntimeError('Decoded payload differs from the synthetic input')
        print(f'Compressed={compressed}; frame size={len(frame)} bytes; payload matches')
    print('Offline round-trip: OK')


if __name__ == '__main__':
    main()
