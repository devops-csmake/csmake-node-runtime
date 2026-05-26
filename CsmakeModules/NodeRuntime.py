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
import subprocess

from CsmakeCore.CsmakeModuleAllPhase import CsmakeModuleAllPhase


class NodeRuntime(CsmakeModuleAllPhase):
    """Purpose: Execute a Node.js script
       Type: Module   Library: csmake-ghactions
       Phases: *any*
       Options:
           --main    - path to the Node.js entry-point script
           --pre     - (OPTIONAL) path to a pre-script run before --main
           --post    - (OPTIONAL) path to a post-script run after --main
           <key>=<value> - environment variables forwarded to node (all keys
                           that do NOT start with '--')
       Notes:
           Raises a non-zero exit as a build failure.  The caller is
           responsible for setting any protocol-specific variables
           (e.g. GITHUB_OUTPUT, INPUT_*) in the env dict when calling
           execute() directly.
       Example:
           [NodeRuntime@lint]
           --main=scripts/lint.js
           NODE_ENV=production
           OUTPUT_DIR=dist
    """

    REQUIRED_OPTIONS = ['--main']

    def default(self, options):
        main = options['--main'].strip()
        pre  = options.get('--pre',  '').strip() or None
        post = options.get('--post', '').strip() or None
        env  = dict(os.environ)
        env.update({k: v.strip() for k, v in options.items() if not k.startswith('--')})
        cwd = os.getcwd()
        try:
            if pre:
                self.execute(pre, env, cwd)
            self.execute(main, env, cwd)
            if post:
                self.execute(post, env, cwd)
            self.log.passed()
            return True
        except Exception as e:
            self.log.error("NodeRuntime failed: %s", str(e))
            self.log.failed()
            return None

    # ------------------------------------------------------------------ #
    # Python-callable interface (used by GHActions and other modules)     #
    # ------------------------------------------------------------------ #

    def execute(self, script_path, env, cwd):
        """Run a Node.js script synchronously.

        script_path - absolute or relative path to the .js entry point
        env         - full environment dict for the subprocess
        cwd         - working directory for the subprocess

        Raises RuntimeError on non-zero exit so the caller can decide how
        to handle the failure (log, propagate, etc.)."""
        rc = subprocess.call(['node', script_path], env=env, cwd=cwd)
        if rc != 0:
            raise RuntimeError(
                "node '%s' exited with code %d" % (script_path, rc))
