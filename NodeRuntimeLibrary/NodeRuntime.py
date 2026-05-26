# <copyright>
# (c) Copyright 2025 Autumn Patterson
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# </copyright>
"""Pure-Python library for locating and invoking a Node.js interpreter.

Intended to be imported by other csmake modules (e.g. GHActions) rather
than used directly as a csmake section.  If you need a first-class csmake
module that runs Node.js scripts, use the NodeRuntime csmake module from
a future csmake-node-runtime-modules package.
"""
import logging
import os
import shutil
import subprocess

_log = logging.getLogger(__name__)

# Common installation paths checked as a last resort when node is not on PATH.
_NODE_FALLBACK_PATHS = [
    '/usr/local/bin/node',
    '/usr/bin/node',
    '/usr/bin/nodejs',              # Debian/Ubuntu historic name
    '/opt/homebrew/bin/node',       # Apple Silicon Homebrew
    '/usr/local/opt/node/bin/node', # Intel Homebrew
]


class NodeRuntime:
    """Locate and invoke a Node.js interpreter.

    Usage::

        runner = NodeRuntime()              # auto-discover node
        runner = NodeRuntime(node='/path/to/node')   # explicit override
        runner.execute('dist/index.js', env, cwd)

    The node binary is resolved in this order:
      1. ``node`` constructor argument
      2. ``NODE`` environment variable (from *env*)
      3. ``$NVM_BIN/node`` (from *env*)
      4. ``node`` on PATH
      5. ``nodejs`` on PATH  (Debian/Ubuntu legacy name)
      6. Common hardcoded fallback paths

    Raises ``RuntimeError`` if no usable binary is found or a script exits
    non-zero.
    """

    def __init__(self, node=None):
        """
        node - explicit path to the node binary, or None for auto-discovery.
        """
        self._node_override = node

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def execute(self, script_path, env, cwd):
        """Run a Node.js script synchronously.

        script_path - absolute or relative path to the .js entry point
        env         - full environment dict for the subprocess
        cwd         - working directory for the subprocess

        Raises RuntimeError on non-zero exit.
        """
        node_bin = self._resolve_node(self._node_override, env)
        rc = subprocess.call([node_bin, script_path], env=env, cwd=cwd)
        if rc != 0:
            raise RuntimeError(
                "node '%s' exited with code %d" % (script_path, rc))

    # ------------------------------------------------------------------ #
    # Node binary resolution                                               #
    # ------------------------------------------------------------------ #

    def _resolve_node(self, override, env):
        """Return the path to a usable node binary.

        Raises RuntimeError if nothing is found.
        """
        candidates = []

        if override:
            candidates.append(('constructor override', override))

        node_env = (env or {}).get('NODE', '').strip()
        if node_env:
            candidates.append(('NODE env var', node_env))

        nvm_bin = (env or {}).get('NVM_BIN', '').strip()
        if nvm_bin:
            candidates.append(('NVM_BIN', os.path.join(nvm_bin, 'node')))

        # PATH-based lookups — shutil.which honours the env PATH.
        for name in ('node', 'nodejs'):
            found = shutil.which(name, path=(env or {}).get('PATH'))
            if found:
                candidates.append(('PATH', found))
                break  # 'node' found; no need to try 'nodejs'

        for path in _NODE_FALLBACK_PATHS:
            candidates.append(('fallback', path))

        for source, path in candidates:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                _log.debug("Using node binary from %s: %s", source, path)
                return path

        raise RuntimeError(
            "Cannot find a node binary. Install Node.js or pass "
            "node=<path> to NodeRuntime(). "
            "Searched: %s" % ', '.join(p for _, p in candidates))
