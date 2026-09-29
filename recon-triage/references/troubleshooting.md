# Troubleshooting Guide

## Common Issues

### Slither Not Found

**Symptom**: `slither . --json slither.json` returns "command not found"

**Fix**: Install Slither via pip or Foundry:
```bash
pip install slither-analyzer
# or
foundryup && which slither
```

### Cast Not Available

**Symptom**: `cast call <ADDRESS> ...` returns "command not found"

**Fix**: Install Foundry:
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### Python Inspector Failures

**Symptom**: `python3 scripts/audit_inspector.py` crashes or produces empty output

**Fix**: Verify Solidity source is present and compiler version matches:
```bash
# Check source exists
ls -R /path/to/contracts/

# Ensure solc version matches
solc --version
```

### jq Filter Errors

**Symptom**: `cat slither.json | jq '...'` produces parsing errors

**Fix**: Validate JSON output first:
```bash
slither . --json slither.json | python3 -c "import sys,json; json.load(sys.stdin)"
```

### Memory Issues with Large Contracts

**Symptom**: Slither runs out of memory on large codebases

**Fix**: Run with reduced analysis scope:
```bash
slither . --json slither.json --max-polys 50
```

### Proxy Resolution Fails

**Symptom**: Tiers 1-2 cannot resolve implementation address

**Fix**: Verify RPC URL is responsive and contract is verified on explorer:
```bash
# Test RPC
cast rpc eth_blockNumber

# Check verification status via Etherscan API
```

## Error Code Reference

| Error | Meaning | Resolution |
|---|---|---|
| `1` | General failure | Check input validity |
| `1` | Invalid address format | Verify checksum address |
| `1` | RPC timeout | Retry or switch endpoint |