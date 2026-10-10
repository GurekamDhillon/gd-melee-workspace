#pragma once

namespace wb {
// Checks option tokens before QApplication exists, skipping values of existing
// launcher options so a path/disc named "--mcp" remains an ordinary value.
bool isWorkbenchCli(int argc, char **argv);
// Requires a QCoreApplication. --mcp serves agents; --wb-call is the human path.
int runWorkbenchCli(int argc, char **argv);
} // namespace wb
