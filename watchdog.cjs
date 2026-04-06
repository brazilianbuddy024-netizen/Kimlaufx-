const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const LOG = fs.openSync('/tmp/watchdog.log', 'a');

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  fs.writeSync(LOG, line);
}

function start() {
  const child = spawn('node', ['.next/standalone/server.js', '--port', '3000'], {
    cwd: __dirname,
    stdio: ['pipe', fs.openSync('/tmp/nextjs-prod.log', 'a'), fs.openSync('/tmp/nextjs-prod.log', 'a')],
    detached: false,
  });
  
  log(`Started production server PID ${child.pid}`);
  
  child.on('exit', (code) => {
    log(`Exited code ${code}, restarting in 2s`);
    setTimeout(start, 2000);
  });
  
  child.on('error', (err) => {
    log(`Error: ${err.message}, restarting`);
    setTimeout(start, 2000);
  });
}

start();
