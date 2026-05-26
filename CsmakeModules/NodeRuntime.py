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
import os
import shutil
import subprocess

from CsmakeCore.CsmakeModuleAllPhase import CsmakeModuleAllPhase


# Common installation paths checked as a last resort when node is not on PATH.
_NODE_FALLBACK_PATHS = [
    '/usr/local/bin/node',
    '/usr/bin/node',
    '/usr/bin/nodejs',          # Debian/Ubuntu historic name
    '/opt/homebrew/bin/node',   # Apple Silicon Homebrew
    '/usr/local/opt/node/bin/node',  # Intel Homebrew
]


class NodeRuntime(CsmakeModuleAllPhase):
    """Purpose: Execute a Node.js script
       Type: Module   Library: csmake-node-runtime
       Phases: *any*
       Options:
           --main    - path to the Node.js entry-point script (REQUIRED)
           --node    - (OPTIONAL) explicit path to the node binary.
                       Overrides all automatic discovery.
           --pre     - (OPTIONAL) path to a pre-script run before --main
           --post    - (OPTIONAL) path to a post-script run after --main
           <key>=<value> - environment variables forwarded to node (all keys
                           that do NOT start with '--')
       Notes:
           The node binary is resolved in this order:
             1. --node option (if supplied)
             2. NODE environment variable
             3. $NVM_BIN/node  (for nvm-managed installs)
             4. 'node' on PATH  (shutil.which)
             5. 'nodejs' on PATH  (Debian/Ubuntu legacy name)
             6. Common hardcoded paths as a last resort
           A non-zero exit from any script is treated as a build failure.
           The caller is responsible for setting any protocol-specific
           variables (e.g. GITHUB_OUTPUT, INPUT_*) in the env dict when
           calling execute() directly.
       Example:
           [NodeRuntime@lint]
           --main=scripts/lint.js
           NODE_ENV=production
           OUTPUT_DIR=dist

           [NodeRuntime@custom-node]
           --node=/opt/nvm/versions/node/v20.11.0/bin/node
           --main=scripts/build.js
    """

    REQUIRED_OPTIONS = ['--main']

    def default(self, options):
        main = options['--main'].strip()
        pre  = options.get('--pre',  '').strip() or None
        post = options.get('--post', '').strip() or None

        env  = dict(os.environ)
        env.update({k: v.strip() for k, v in options.items() if not k.startswith('--')})

        node_override = options.get('--node', '').strip() or None

        try:
            node_bin = self._resolve_node(node_override, env)
        except RuntimeError as e:
            self.log.error(str(e))
            self.log.failed()
            return None

        cwd = os.getcwd()
        try:
            if pre:
                self.execute(pre, env, cwd, node_bin=node_bin)
            self.execute(main, env, cwd, node_bin=node_bin)
            if post:
                self.execute(post, env, cwd, node_bin=node_bin)
            self.log.passed()
            return True
        except Exception as e:
            self.log.error("NodeRuntime failed: %s", str(e))
            self.log.failed()
            return None

    # ------------------------------------------------------------------ #
    # Python-callable interface (used by GHActions and other modules)     #
    # ------------------------------------------------------------------ #

    def execute(self, script_path, env, cwd, node_bin=None):
        """Run a Node.js script synchronously.

        script_path - absolute or relative path to the .js entry point
        env         - full environment dict for the subprocess
        cwd         - working directory for the subprocess
        node_bin    - explicit path to the node binary; resolved
                      automatically from env when omitted

        Raises RuntimeError on non-zero exit so the caller can decide how
        to handle the failure (log, propagate, etc.)."""
        if node_bin is None:
            node_bin = self._resolve_node(None, env)
        rc = subprocess.call([node_bin, script_path], env=env, cwd=cwd)
        if rc != 0:
            raise RuntimeError(
                "node '%s' exited with code %d" % (script_path, rc))

    # ------------------------------------------------------------------ #
    # Node binary resolution                                               #
    # ------------------------------------------------------------------ #

    def _resolve_node(self, override, env):
        """Return the path to the node binary.

        Resolution order:
          1. override argument (from --node option)
          2. NODE environment variable
          3. $NVM_BIN/node
          4. 'node' on PATH
          5. 'nodejs' on PATH
          6. Common hardcoded fallback paths

        Raises RuntimeError if no usable node binary is found.
        """
        candidates = []

        if override:
            candidates.append(('--node option', override))

        node_env = env.get('NODE', '').strip()
        if node_env:
            candidates.append(('NODE env var', node_env))

        nvm_bin = env.get('NVM_BIN', '').strip()
        if nvm_bin:
            candidates.append(('NVM_BIN', os.path.join(nvm_bin, 'node')))

        # PATH-based lookups — shutil.which honours the env PATH.
        for name in ('node', 'nodejs'):
            found = shutil.which(name, path=env.get('PATH'))
            if found:
                candidates.append(('PATH', found))
                break  # first match wins; no need to try 'nodejs' if 'node' found

        for path in _NODE_FALLBACK_PATHS:
            candidates.append(('fallback', path))

        for source, path in candidates:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                self.log.debug("Using node binary from %s: %s", source, path)
                return path

        raise RuntimeError(
            "Cannot find a node binary. Install Node.js or supply --node=<path>. "
            "Searched: %s" % ', '.join(p for _, p in candidates))
