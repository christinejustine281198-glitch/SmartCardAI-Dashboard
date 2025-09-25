
// runner.js
// Minimal Node.js runner for Flask app

const vm = require("vm");

// Get code from command line
const code = process.argv[2] || "";

let logs = [];
let result = null;

// Override console.log to capture logs
const sandbox = {
    console: {
        log: (...args) => logs.push(args.join(" "))
    }
};

try {
    const script = new vm.Script(code);
    const context = new vm.createContext(sandbox);
    result = script.runInContext(context);
} catch (err) {
    console.error(err.toString());
    process.exit(1);
}

// Output JSON
console.log(JSON.stringify({ logs, result }));
