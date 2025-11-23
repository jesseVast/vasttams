const { spawn } = require('node:child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

// Detect if we're in Docker/production environment
function isProduction() {
  // Check for Docker environment
  if (fs.existsSync('/.dockerenv')) {
    return true;
  }
  // Check for CI environment
  if (process.env.CI === 'true' || process.env.CI === '1') {
    return true;
  }
  // Check for production NODE_ENV
  if (process.env.NODE_ENV === 'production') {
    return true;
  }
  return false;
}

// Run react-scripts with conditional Node.js options
// The --localstorage-file option is needed for local development (Node.js 20+)
// but causes build failures in Docker/production, so we skip it there
module.exports = function runReactScript(scriptName) {
  const scriptPath = require.resolve(`react-scripts/scripts/${scriptName}`);
  const args = [];
  
  // Only add --localstorage-file for local development
  if (!isProduction()) {
    const nodeVersion = process.version.match(/^v(\d+)/)?.[1];
    if (nodeVersion && parseInt(nodeVersion) >= 20) {
      const tempFile = path.join(os.tmpdir(), '.localstorage-webpack-temp');
      args.push(`--localstorage-file=${tempFile}`);
    }
  }
  
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

