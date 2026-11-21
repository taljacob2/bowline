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

//
// One hook is answered here when it can be, without Python: the crew's check before an edit. It runs before every
// Edit, Write and NotebookEdit of every session, and in most repositories it has nothing to say, because the
// repository has one worktree. Starting Python for that costs a few tenths of a second per edit, and over a second on
// a machine that is busy, so this file first looks whether the edited file's repository has another worktree at all.

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, isAbsolute, join } from "node:path";
import { fileURLToPath } from "node:url";

const entry = join(dirname(fileURLToPath(import.meta.url)), "bowline.py");
const words = process.argv.slice(2);
const windows = process.platform === "win32";
const candidates = windows ? [["python"], ["py", "-3"], ["python3"]] : [["python3"], ["python"]];

// On Windows, `python` and `python3` can be the Microsoft Store's placeholders, which are on the PATH even when no
// Python is installed; they exit with this code after printing a hint, which here means: try the next name.
const STORE_PLACEHOLDER = 9009;

// Whether the check before an edit has nothing to say about this tool call, told from the hook's JSON alone: no
// absolute file path, a file outside every repository, or a repository whose git folder lists no other worktree.
// A repository's main checkout keeps one folder per other worktree under .git/worktrees. A worktree's own .git is a
// file, which already means there are at least two, so Python decides.
function nothingToSayBeforeEdit(text) {
  let path;
  try {
    const input = JSON.parse(text).tool_input || {};
    path = input.file_path || input.notebook_path;
  } catch {
    return true;
  }
  if (typeof path !== "string" || !isAbsolute(path)) {
    return true;
  }
  for (let folder = dirname(path); ; folder = dirname(folder)) {
    const dot = join(folder, ".git");
    if (existsSync(dot)) {
      try {
        if (!statSync(dot).isDirectory()) {
          return false;
        }
        const others = join(dot, "worktrees");
        return !existsSync(others) || !readdirSync(others, { withFileTypes: true }).some((e) => e.isDirectory());
      } catch {
        return false;
      }
    }
    if (dirname(folder) === folder) {
      return true;
    }
  }
}

// Standard input goes to Python as it is, except for the check before an edit, which is read here first.
let stdio = "inherit";
let input;
if (words.join(" ") === "crew before-edit --hook") {
  try {
    input = readFileSync(0, "utf8");
  } catch {
    input = "";
  }
  if (nothingToSayBeforeEdit(input)) {
    process.exit(0);
  }
  stdio = ["pipe", "inherit", "inherit"];
}

for (const [program, ...before] of candidates) {
  const result = spawnSync(program, [...before, "-I", entry, ...words], { stdio, input, windowsHide: true });
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
