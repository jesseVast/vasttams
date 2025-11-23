const { spawn } = require('node:child_process');

// Run react-scripts without custom Node.js options
// The --localstorage-file option was invalid and caused build failures
module.exports = function runReactScript(scriptName) {
  const scriptPath = require.resolve(`react-scripts/scripts/${scriptName}`);
  
  const child = spawn(
    process.execPath,
    [scriptPath],
    {
      stdio: 'inherit',
      env: process.env,
    },
  );

  child.on('close', (code) => {
    process.exit(code);
  });
};

