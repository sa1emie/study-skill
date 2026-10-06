// Validate every $...$ and $$...$$ expression in a markdown file with KaTeX,
// the renderer most chat apps use. Needs katex next to this file:
//   cd <skill>/scripts && npm install --no-save katex
//   node <skill>/scripts/katex_check.js out/<file>.md
// Exit 0 = every expression renders, 1 = errors (listed), 2 = usage.
const path = require('path');
let katex;
try { katex = require(path.join(__dirname, 'node_modules', 'katex')); }
catch (e) { console.log('katex not installed: cd ' + __dirname + ' && npm install --no-save katex'); process.exit(2); }
const fs = require('fs');
const f = process.argv[2];
if (!f) { console.log('usage: node katex_check.js <file.md>'); process.exit(2); }
const s = fs.readFileSync(f, 'utf8');
const d = [...s.matchAll(/\$\$([\s\S]+?)\$\$/g)].map(m => m[1]);
const i = [...s.replace(/\$\$[\s\S]+?\$\$/g, '').matchAll(/(?<!\$)\$([^$\n]+?)\$(?!\$)/g)].map(m => m[1]);
const e = [];
const run = (a, mode) => a.forEach(x => {
  try { katex.renderToString(x.trim(), { displayMode: mode, throwOnError: true }); }
  catch (err) { e.push(x.trim().slice(0, 60) + '  ->  ' + err.message.slice(0, 100)); }
});
run(d, true); run(i, false);
console.log('display: ' + d.length + '  inline: ' + i.length + '  errors: ' + e.length);
e.slice(0, 20).forEach(x => console.log('  ' + x));
process.exit(e.length ? 1 : 0);
