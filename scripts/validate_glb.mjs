#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { pathToFileURL, fileURLToPath } from 'node:url';

async function loadValidator() {
  try {
    const loaded = await import('gltf-validator');
    return loaded.default ?? loaded;
  } catch (_) {
    const explicit = process.env.GLTF_VALIDATOR_MODULE;
    const fallback = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../temp_data/node/node_modules/gltf-validator/module.mjs');
    const modulePath = explicit ? path.resolve(explicit) : fallback;
    if (!fs.existsSync(modulePath)) {
      throw new Error('gltf-validator not found. Run npm ci in the repository root.');
    }
    const loaded = await import(pathToFileURL(modulePath).href);
    return loaded.default ?? loaded;
  }
}

const file = process.argv[2];
if (!file) throw new Error('Usage: node scripts/validate_glb.mjs <file.glb>');
const validator = await loadValidator();
const bytes = fs.readFileSync(file);
const report = await validator.validateBytes(new Uint8Array(bytes));
const summary = {
  errors: report.issues.numErrors,
  warnings: report.issues.numWarnings,
  infos: report.issues.numInfos,
  hints: report.issues.numHints,
};
console.log(JSON.stringify(summary, null, 2));
if (summary.errors || summary.warnings) {
  console.error(JSON.stringify(report.issues.messages, null, 2));
  process.exit(1);
}
