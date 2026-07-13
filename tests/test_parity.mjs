// Parity test: the JS engine embedded in fmstyle/web/index.html must produce
// byte-identical output to the Python reference for every fixture case.
//
//   python3 tests/gen_parity_fixtures.py   (after engine changes)
//   node tests/test_parity.mjs

import { readFileSync } from "node:fs";

const root = new URL("..", import.meta.url);
const html = readFileSync(new URL("fmstyle/web/index.html", root), "utf8");

const START = "/* fmstyle-engine-start */";
const END = "/* fmstyle-engine-end */";
const start = html.indexOf(START);
const end = html.indexOf(END);
if (start === -1 || end === -1) {
  console.error("engine markers not found in index.html");
  process.exit(2);
}
(0, eval)(html.slice(start + START.length, end));

const { formatCalc, lintCalc, makeStyle } = globalThis.FMSTYLE;
const cases = JSON.parse(readFileSync(new URL("tests/parity_fixtures.json", root), "utf8"));

let failures = 0;
for (const c of cases) {
  const style = makeStyle(c.style || {});
  let out;
  try {
    out = formatCalc(c.source, style);
  } catch (e) {
    out = "ERROR: " + e.message;
  }
  if (out !== c.expected) {
    failures++;
    console.log("FAIL format:", JSON.stringify(c.source));
    console.log("  python:", JSON.stringify(c.expected));
    console.log("  js:    ", JSON.stringify(out));
  }
  let lint;
  try {
    lint = lintCalc(c.source, style).map((issue) => issue[0]);
  } catch (e) {
    lint = ["ERROR: " + e.message];
  }
  if (JSON.stringify(lint) !== JSON.stringify(c.lint)) {
    failures++;
    console.log("FAIL lint:", JSON.stringify(c.source));
    console.log("  python:", JSON.stringify(c.lint));
    console.log("  js:    ", JSON.stringify(lint));
  }
}

if (failures) {
  console.error(`${failures} parity failure(s) over ${cases.length} cases`);
  process.exit(1);
}
console.log(`parity OK: ${cases.length} cases, JS === Python`);
