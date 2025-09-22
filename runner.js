

// Simple Node.js runner for JS files
const fs = require("fs");
const path = require("path");

const filePath = process.argv[2];
if (!filePath) {
    console.error("No file provided");
    process.exit(1);
}

try {
    const code = fs.readFileSync(filePath, "utf-8");
    const result = eval(code);
    console.log(result);
} catch (err) {
    console.error(err);
}
