const fs = require('node:fs');
const runtime = `GitHub Actions vendor runtime: ${process.version} (${process.platform}/${process.arch})`;
console.log(runtime);
const [major, minor, patch] = process.versions.node.split('.').map(Number);
const stable = /^\d+\.\d+\.\d+$/.test(process.versions.node);
const patched = stable && major === 24 && (minor > 22 || (minor === 22 && patch >= 1));
const result = patched
  ? 'The Node 24 runtime meets the 24.22.1 security baseline.'
  : 'Vendor exception: this runtime does not meet the Node 24.22.1 baseline. GitHub owns the runner distribution.';
console.log(result);
if (!patched) console.log(`::warning::${result}`);
fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${runtime}\n\n${result}\n`);
