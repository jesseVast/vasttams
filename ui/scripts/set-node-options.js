const { spawn } = require('node:child_process');

// --no-experimental-webstorage was removed in Node.js 20+
// Only use it for older Node versions
const nodeVersion = process.version.match(/^v(\d+)/)?.[1];
const WEBSTORAGE_FLAG = nodeVersion && parseInt(nodeVersion) < 20 ? '--no-experimental-webstorage' : null;

module.exports = function runReactScript(scriptName) {
  const scriptPath = require.resolve(`react-scripts/scripts/${scriptName}`);

  const args = WEBSTORAGE_FLAG ? [WEBSTORAGE_FLAG, scriptPath] : [scriptPath];

  const child = spawn(
    process.execPath,
    args,
    {
      stdio: 'inherit',
      env: process.env,
    },
  );

  child.on('close', (code) => {
    process.exit(code);
  });
};

