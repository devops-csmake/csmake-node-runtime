// Integration smoke-test: verify the node binary works and report its version.
// Exit 0 on success, 1 if the version is unexpectedly old.
'use strict';

const [major] = process.versions.node.split('.').map(Number);

console.log('node version:', process.versions.node);
console.log('platform:    ', process.platform, process.arch);

if (major < 14) {
    console.error('ERROR: Node.js 14 or newer is required (found ' + process.versions.node + ')');
    process.exit(1);
}

console.log('OK: node runtime check passed');
