#!/usr/bin/env node
/**
 * Standalone Frontier Verify receipt verifier -- JavaScript / Node.js.
 *
 * Uses ONLY Node's built-in `crypto` module (native Ed25519 support since
 * Node 12) -- zero npm dependencies, zero shared code with the Python
 * implementation. See docs/protocol/independent-verification.md,
 * "Common-mode risk analysis," for exactly what this second
 * implementation does and does not buy in terms of genuine independence
 * from the Python standalone verifier and the reference implementation.
 *
 * Cross-checked against BOTH the Python reference implementation and the
 * Python standalone verifier on every test run --
 * tests/conformance/test_cross_language_verifier_agrees.py invokes this
 * file as a subprocess and confirms all three agree.
 *
 * Usage:
 *   node verify_receipt.js receipt.json <verifier_public_key_hex>
 *
 * Exit code 0 if the signature is valid, 1 otherwise.
 */
'use strict';

const fs = require('fs');
const crypto = require('crypto');

/** Deliberately RE-IMPLEMENTED, not ported by copying the Python or the
 * JS source of each other -- see this file's module docstring. Must
 * produce byte-identical output to
 * frontier_verify.core.canonical.canonicalize() and
 * tools/standalone-verifier/verify_receipt.py's canonicalize() for the
 * same logical content: sorted keys (recursively), no insignificant
 * whitespace, UTF-8. */
function sortKeysDeep(value) {
  if (Array.isArray(value)) {
    return value.map(sortKeysDeep);
  }
  if (value !== null && typeof value === 'object') {
    const sorted = {};
    for (const key of Object.keys(value).sort()) {
      sorted[key] = sortKeysDeep(value[key]);
    }
    return sorted;
  }
  return value;
}

function canonicalize(obj) {
  // JSON.stringify with no indent argument already produces compact
  // output (no spaces after ':' or ',') and does not escape non-ASCII by
  // default -- matching Python's separators=(",", ":"), ensure_ascii=False.
  return JSON.stringify(sortKeysDeep(obj));
}

/** Ed25519 public keys are represented as raw 32-byte hex throughout this
 * project. Node's crypto module doesn't take raw bytes directly for
 * Ed25519 -- JWK (RFC 8037, base64url-encoded raw key as "x") is the
 * standard, dependency-free way to wrap them into a usable KeyObject. */
function publicKeyFromHex(hexStr) {
  const rawBytes = Buffer.from(hexStr, 'hex');
  const x = rawBytes.toString('base64url');
  return crypto.createPublicKey({
    key: { kty: 'OKP', crv: 'Ed25519', x },
    format: 'jwk',
  });
}

function verifyReceipt(receipt, publicKeyHex) {
  const signatureB64 = receipt.signature;
  if (!signatureB64) {
    return false;
  }
  const payload = Object.assign({}, receipt);
  delete payload.signature;
  const message = Buffer.from(canonicalize(payload), 'utf-8');

  try {
    const signature = Buffer.from(signatureB64, 'base64');
    const publicKey = publicKeyFromHex(publicKeyHex);
    // Ed25519's hash is built into the algorithm -- pass null, not a
    // digest name, matching Node's documented Ed25519 usage.
    return crypto.verify(null, message, publicKey, signature);
  } catch (e) {
    return false;
  }
}

function main() {
  const args = process.argv.slice(2);
  if (args.length !== 2) {
    console.log(
      'Usage: node verify_receipt.js receipt.json <verifier_public_key_hex>'
    );
    process.exit(2);
  }
  const [receiptPath, publicKeyHex] = args;
  const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf-8'));

  const ok = verifyReceipt(receipt, publicKeyHex);
  console.log(`signature_valid=${ok}`);
  if (ok) {
    console.log(`verifier_key_id=${receipt.verifier_key_id}`);
    console.log(`assurance_level=${receipt.assurance_level}`);
    console.log(`result=${receipt.result}`);
    for (const limitation of receipt.limitations || []) {
      console.log(`  limitation: ${limitation}`);
    }
  }
  process.exit(ok ? 0 : 1);
}

if (require.main === module) {
  main();
}

module.exports = { canonicalize, verifyReceipt, publicKeyFromHex };
