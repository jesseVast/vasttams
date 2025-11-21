const { spawn } = require('node:child_process');
const os = require('os');
const path = require('path');

// Disable localStorage for webpack builds
const nodeVersion = process.version.match(/^v(\d+)/)?.[1];
const args = [];

if (nodeVersion && parseInt(nodeVersion) >= 20) {
  // Node 20+ requires a file path for localStorage or we need to disable it
  // Use a temp file that gets cleaned up
  const tempFile = path.join(os.tmpdir(), '.localstorage-webpack-temp');
  args.push(`--localstorage-file=${tempFile}`);
}

module.exports = function runReactScript(scriptName) {
  const scriptPath = require.resolve(`react-scripts/scripts/${scriptName}`);
  args.push(scriptPath);

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

