"""Send a file safely to the QNX unit as hex over its Telnet console."""
import argparse
import getpass
import hashlib
import os
import socket
import time


def negotiate(sock, data):
    clean = bytearray()
    index = 0
    while index < len(data):
        if data[index] == 255 and index + 2 < len(data):
            command, option = data[index + 1], data[index + 2]
            sock.sendall(bytes((255, 254 if command in (251, 252) else 252, option)))
            index += 3
        else:
            clean.append(data[index])
            index += 1
    return bytes(clean)


def expect(sock, token, timeout=15):
    data = bytearray()
    deadline = time.time() + timeout
    while token not in data:
        if time.time() >= deadline:
            raise TimeoutError("Telnet prompt not received: " + repr(token))
        try:
            data.extend(negotiate(sock, sock.recv(8192)))
        except TimeoutError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument("--host", default="172.16.250.248")
    parser.add_argument("--user", default="root")
    parser.add_argument(
        "--binary",
        action="store_true",
        help="write the decoded payload directly; Telnet IAC bytes are escaped",
    )
    parser.add_argument(
        "--octal",
        action="store_true",
        help="write binary safely through QNX ksh printf octal escapes",
    )
    args = parser.parse_args()
    password = os.environ.get("CW_TELNET_PASSWORD") or getpass.getpass()
    if args.binary and args.octal:
        parser.error("--binary and --octal are mutually exclusive")
    payload = open(args.source, "rb").read()
    sock = socket.create_connection((args.host, 23), timeout=10)
    sock.settimeout(0.25)
    expect(sock, b"login:")
    sock.sendall((args.user + "\n").encode("ascii"))
    expect(sock, b"Password:")
    sock.sendall((password + "\n").encode("ascii"))
    expect(sock, b"# ")
    target = args.target if (args.binary or args.octal) else args.target + ".hex"
    if args.octal:
        commands = ["rm -f " + target, ": > " + target]
        for offset in range(0, len(payload), 48):
            escaped = "".join("\\%03o" % byte for byte in payload[offset : offset + 48])
            commands.append("printf '" + escaped + "' >> " + target)
        commands.append("echo CW_OCTAL_DONE")
        sock.sendall(("\n".join(commands) + "\n").encode("ascii"))
        expect(sock, b"CW_OCTAL_DONE", timeout=120)
        sock.close()
        print("SIZE=" + str(len(payload)) + " SHA256=" + hashlib.sha256(payload).hexdigest())
        return
    sock.sendall(("rm -f " + target + "; : > " + target + "; echo CW_BEGIN\n").encode("ascii"))
    expect(sock, b"CW_BEGIN")
    sock.sendall(bytes((255, 251, 0, 255, 253, 0)))
    time.sleep(0.2)
    sock.sendall(("stty raw -echo; cat > " + target + "\n").encode("ascii"))
    time.sleep(0.5)
    wire_payload = payload.replace(b"\xff", b"\xff\xff") if args.binary else payload.hex().encode("ascii")
    sock.sendall(wire_payload)
    sock.shutdown(socket.SHUT_WR)
    time.sleep(1)
    sock.close()
    print("SIZE=" + str(len(payload)) + " SHA256=" + hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    main()
