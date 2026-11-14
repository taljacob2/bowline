// bowline's launcher for the plugin's hooks and skills: finds Python 3 by the name this machine gives it and runs
// scripts/bowline.py with the same arguments, passing standard input, standard output and the exit code through.
//
//     node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" doctor --brief
//
// Claude Code starts each hook as the program `node` with this file and the command's words as its arguments, with no
// shell in between. On Windows a hook given that way must name a real program, and node.exe is one; Claude Code's
// hooks documentation gives this node-and-script form as the one that works on every system. Python has no single
// name that does: Windows usually has `python` and the `py` launcher, while macOS and Linux have `python3`. So this
// file tries the names in the order each system makes likely and uses the first one that runs.

import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const entry = join(dirname(fileURLToPath(import.meta.url)), "bowline.py");
const words = process.argv.slice(2);
const windows = process.platform === "win32";
const candidates = windows ? [["python"], ["py", "-3"], ["python3"]] : [["python3"], ["python"]];

// On Windows, `python` and `python3` can be the Microsoft Store's placeholders, which are on the PATH even when no
// Python is installed; they exit with this code after printing a hint, which here means: try the next name.
const STORE_PLACEHOLDER = 9009;

for (const [program, ...before] of candidates) {
  const result = spawnSync(program, [...before, "-I", entry, ...words], { stdio: "inherit", windowsHide: true });
  if (result.error && result.error.code === "ENOENT") {
    continue;
  }
  if (result.error) {
    process.stderr.write(`bowline: ${program} could not be started (${result.error.message}).\n`);
    process.exit(1);
  }
  if (windows && result.status === STORE_PLACEHOLDER) {
    continue;
  }
  process.exit(result.status === null ? 1 : result.status);
}

const tried = candidates.map((c) => c.join(" ")).join(", ");
process.stderr.write(
  `bowline: Python 3 was not found on this machine (tried ${tried}).\n` +
  "bowline's tools are Python scripts, so its hooks and skills cannot run without it.\n" +
  "Install Python 3.8 or later so that one of those names is on the PATH, then start a new Claude Code session.\n"
);
// Exit 1, not 2: a hook that exits with 2 blocks what Claude was doing, and a missing Python must not block a commit.
process.exit(1);
