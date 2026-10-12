#!/usr/bin/env python3
"""Offline, explicit-fork gas lower bounds for unsigned type-2 transactions."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rpc-unsigned-reader'))
import rpc_reader as reader

PROFILES = ('london', 'shanghai', 'prague')
MAX_INPUT_CHARS = reader.MAX_JSON_CHARS


def inspect(text, profile, input_format='rlp'):
    """Parse original unsigned input, then compute bounds without executing it.

    Explicit historical profiles, not network/fork detection. Never accept a
    precomputed summary as evidence. No input files or external state are read.
    """
    if profile not in PROFILES:
        raise ValueError('choose london, shanghai or prague explicitly')
    if input_format not in ('rlp', 'json'):
        raise ValueError('input format must be rlp or json')
    if not isinstance(text, str) or len(text) > MAX_INPUT_CHARS:
        raise ValueError('input exceeds 512 Ki characters or is not text')
    evidence = (reader.inspect_json(text)['inspection'] if input_format == 'json'
                else reader.intent.interpret(text))
    tx = evidence['transaction']
    # RLP decoder intentionally accepts larger integers structurally. This
    # diagnostic bounds them before computing protocol gas components.
    for field in ('chainId', 'nonce', 'maxPriorityFeePerGas', 'maxFeePerGas',
                  'gasLimit', 'value'):
        if int(tx[field]) >= 2**256:
            raise ValueError(field + ' exceeds this diagnostic\'s uint256 bound')
    data = bytes.fromhex(tx['data'][2:])
    zeroes = data.count(0)
    nonzeroes = len(data) - zeroes
    tokens = zeroes + 4 * nonzeroes
    addresses = len(tx['accessList'])
    keys = sum(len(entry['storageKeys']) for entry in tx['accessList'])
    unique_addresses = len({entry['address'] for entry in tx['accessList']})
    unique_keys = len({(entry['address'], key) for entry in tx['accessList']
                       for key in entry['storageKeys']})
    creation = tx['to'] is None
    words = (len(data) + 31) // 32 if creation else 0
    metered_initcode = creation and profile != 'london'
    parts = {'baseGas': 21000, 'zeroByteGas': 4 * zeroes,
             'nonzeroByteGas': 16 * nonzeroes,
             'accessAddressGas': 2400 * addresses, 'accessStorageKeyGas': 1900 * keys,
             'creationGas': 32000 if creation else 0,
             'initcodeWordGas': 2 * words if metered_initcode else 0}
    intrinsic = sum(parts.values())
    floor = 21000 + 10 * tokens if profile == 'prague' else None
    minimum = max(intrinsic, floor or 0)
    gas_limit = int(tx['gasLimit'])
    enough = gas_limit >= minimum
    initcode_ok = len(data) <= 49152 if metered_initcode else None
    violations = []
    if not enough:
        violations.append('gas-limit-below-required-minimum')
    if initcode_ok is False:
        violations.append('initcode-exceeds-49152-bytes')
    if int(tx['maxPriorityFeePerGas']) > int(tx['maxFeePerGas']):
        violations.append('priority-fee-exceeds-max-fee')
    warnings = list(evidence['warnings'])
    if addresses != unique_addresses or keys != unique_keys:
        warnings.append('Duplicate access-list occurrences are charged separately, not deduplicated.')
    warnings.append('Explicit historical gas profile only; no activation, execution, base fee, block limits, '
                    'balance, nonce, refunds or safety to sign checked. Passing is not transaction validity.')
    return {
        'schema': 'gas-budget/v1', 'profile': profile, 'inputFormat': input_format,
        'inspection': evidence,
        'counts': {name: str(value) for name, value in {
            'dataBytes': len(data), 'zeroBytes': zeroes, 'nonzeroBytes': nonzeroes,
            'calldataTokens': tokens, 'accessAddressOccurrences': addresses,
            'accessStorageKeyOccurrences': keys, 'uniqueAccessAddresses': unique_addresses,
            'uniqueAddressStorageKeyPairs': unique_keys, 'initcodeWords': words}.items()},
        'gas': {'components': {name: str(value) for name, value in parts.items()},
                'intrinsicGas': str(intrinsic),
                'calldataFloorGas': None if floor is None else str(floor),
                'requiredMinimumGasLimit': str(minimum), 'suppliedGasLimit': str(gas_limit),
                'gasLimitMeetsMinimum': enough, 'shortfallGas': str(max(0, minimum - gas_limit)),
                'aboveMinimumGas': str(max(0, gas_limit - minimum)),
                'meaning': 'Lower bound only, not an estimate of EVM execution or gas used.'},
        'initcode': {'isCreation': creation, 'wordMeteringApplied': metered_initcode,
                     'maximumBytes': '49152' if metered_initcode else None,
                     'sizeWithinLimit': initcode_ok},
        'checkedViolations': violations, 'passesCheckedConstraints': not violations,
        'warnings': warnings,
    }


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, choices=PROFILES)
    parser.add_argument('--format', choices=('rlp', 'json'), default='rlp')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--demo', action='store_true')
    source.add_argument('--stdin', action='store_true')
    source.add_argument('--transaction', metavar='TEXT')
    args = parser.parse_args(arguments)
    try:
        if args.demo:
            text = (json.dumps(reader.demo_object()) if args.format == 'json'
                    else reader.D.demo_transaction())
        elif args.stdin:
            text = sys.stdin.read(MAX_INPUT_CHARS + 1)
            # Permit a transport newline for RLP piped from another command.
            # JSON parser handles whitespace itself. Size checked before trim.
            if len(text) > MAX_INPUT_CHARS:
                raise ValueError('input exceeds 512 Ki characters')
            if args.format == 'rlp':
                text = text.removesuffix('\n').removesuffix('\r')
        else:
            text = args.transaction
        result = inspect(text, args.profile, args.format)
    except (ValueError, UnicodeError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['passesCheckedConstraints'] else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
