#!/usr/bin/env python3
"""Capture one read-only Ethereum JSON-RPC response as portable JSON."""
import argparse
import datetime as dt
import json
import ipaddress
import re
import urllib.parse
import sys
import urllib.error
import urllib.request

DEFAULT_RPC = "https://ethereum-rpc.publicnode.com"
USER_AGENT = "Pepeolithic-RPC-Snapshot/2.0 (read-only public data)"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024

# Deliberately small: new methods require an explicit review, never a prefix rule.
READ_METHODS = {
    "eth_blockNumber": 0, "eth_chainId": 0, "net_version": 0,
    "web3_clientVersion": 0, "eth_gasPrice": 0,
    "eth_getBalance": 2, "eth_getTransactionCount": 2, "eth_getCode": 2,
    "eth_getStorageAt": 3, "eth_call": 2,
    "eth_getBlockByNumber": 2, "eth_getBlockByHash": 2,
    "eth_getTransactionByHash": 1, "eth_getTransactionReceipt": 1,
}


def validate_endpoint(endpoint):
    """Return the original URL, or raise ValueError without opening a connection."""
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 2048:
        raise ValueError('endpoint must be nonempty text, at most 2048 characters')
    if any(ord(c) <= 32 or ord(c) >= 127 for c in endpoint) or "\\" in endpoint:
        raise ValueError('endpoint must use printable ASCII without whitespace or backslashes')
    if '?' in endpoint or '#' in endpoint:
        raise ValueError('endpoint must not contain a query or fragment')
    parts = urllib.parse.urlsplit(endpoint)
    if parts.username is not None or parts.password is not None:
        raise ValueError('endpoint must not contain credentials')
    host = parts.hostname
    port = parts.port  # Also rejects malformed/out-of-range ports.
    if not host or (port is not None and port == 0) or parts.netloc.endswith(':'):
        raise ValueError('endpoint requires a host and a valid nonzero port if specified')
    if parts.scheme == 'http' and endpoint.startswith('http://'):
        if (port is not None and parts.netloc == '127.0.0.1:' + str(port)
                and parts.path == '/rpc/1'):
            return endpoint
        raise ValueError('HTTP requires exact 127.0.0.1:<port>/rpc/1')
    if parts.scheme != 'https' or not endpoint.startswith('https://'):
        raise ValueError('HTTPS or exact numeric-loopback HTTP relay required')
    if ':' in host:
        try:
            ipaddress.IPv6Address(host)
        except ValueError as exc:
            raise ValueError('invalid IPv6 host') from exc
    else:
        if len(host) > 253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                                 for label in host.split('.')):
            raise ValueError('invalid ASCII hostname')
    return endpoint



def hex_data(value, byte_count=None):
    if not isinstance(value, str) or not value.startswith("0x"):
        return False
    digits = value[2:]
    return (len(digits) % 2 == 0
            and (byte_count is None or len(digits) == byte_count * 2)
            and all(c in "0123456789abcdefABCDEF" for c in digits))


def block_tag(value):
    if not isinstance(value, str):
        return False
    if value in {"latest", "earliest", "pending", "safe", "finalized"}:
        return True
    return (value.startswith("0x") and bool(value[2:])
            and (value == "0x0" or value[2] != "0")
            and all(c in "0123456789abcdefABCDEF" for c in value[2:]))


def validate_request(method, params):
    if not isinstance(method, str) or method not in READ_METHODS:
        raise ValueError("method is not in the explicit read-only allowlist")
    if not isinstance(params, list) or len(params) != READ_METHODS[method]:
        raise ValueError("wrong parameter count for " + method)
    if method in {"eth_getBalance", "eth_getTransactionCount", "eth_getCode", "eth_getStorageAt"}:
        if not hex_data(params[0], 20) or not block_tag(params[-1]):
            raise ValueError("expected a 20-byte address and a block tag")
        if method == "eth_getStorageAt" and not block_tag(params[1]):
            raise ValueError("storage position must be a hex quantity")
        if method == "eth_getStorageAt" and not params[1].startswith("0x"):
            raise ValueError("storage position must be a hex quantity")
    if method == "eth_call":
        call = params[0]
        if (not isinstance(call, dict) or set(call) - {"to", "data"}
                or not hex_data(call.get("to"), 20)
                or not hex_data(call.get("data", "0x")) or not block_tag(params[1])):
            raise ValueError("eth_call requires only to/data and a block tag")
    if method in {"eth_getBlockByNumber", "eth_getBlockByHash"}:
        valid = block_tag(params[0]) if method.endswith("Number") else hex_data(params[0], 32)
        if not valid or type(params[1]) is not bool:
            raise ValueError("invalid block reference or transaction-detail flag")
    if method in {"eth_getTransactionByHash", "eth_getTransactionReceipt"}:
        if not hex_data(params[0], 32):
            raise ValueError("expected a 32-byte transaction hash")


def validate_response(payload):
    if (not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0"
            or type(payload.get("id")) is not int or payload["id"] != 1):
        raise RuntimeError("invalid JSON-RPC response object, version or id")
    if ("result" in payload) == ("error" in payload):
        raise RuntimeError("response must have exactly one of result or error")
    if "error" in payload:
        error = payload["error"]
        if (not isinstance(error, dict) or type(error.get("code")) is not int
                or not isinstance(error.get("message"), str)):
            raise RuntimeError("malformed JSON-RPC error")
        raise RuntimeError(json.dumps(error, sort_keys=True))
    return payload["result"]



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", nargs="?", default="eth_blockNumber", help="JSON-RPC method (default: eth_blockNumber)")
    parser.add_argument("params", nargs="?", default="[]", help="parameters as a JSON array (default: [])")
    parser.add_argument("--rpc", default=DEFAULT_RPC, help="public Ethereum JSON-RPC endpoint")
    args = parser.parse_args()
    try:
        params = json.loads(args.params)
        validate_request(args.method, params)
        validate_endpoint(args.rpc)
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": args.method, "params": params}).encode()
        request = urllib.request.Request(args.rpc, data=body, headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise RuntimeError("response exceeds 4 MiB limit")
            payload = json.loads(raw.decode("utf-8"))
        validate_response(payload)
    except (ValueError, UnicodeError, OSError, urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        print(f"rpc-snapshot: {exc}", file=sys.stderr)
        return 1
    snapshot = {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "endpoint": args.rpc,
        "method": args.method,
        "params": params,
        "result": payload["result"],
    }
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
