const { spawn } = require('node:child_process');

const WEBSTORAGE_FLAG = '--no-experimental-webstorage';

module.exports = function runReactScript(scriptName) {
  const scriptPath = require.resolve(`react-scripts/scripts/${scriptName}`);

  const child = spawn(
    process.execPath,
    [WEBSTORAGE_FLAG, scriptPath],
    {
      stdio: 'inherit',
      env: process.env,
    },
  );

  child.on('close', (code) => {
    process.exit(code);
  });
};

