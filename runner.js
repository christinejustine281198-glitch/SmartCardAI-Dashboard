let input = "";
process.stdin.setEncoding("utf-8");

process.stdin.on("data", chunk => input += chunk);

process.stdin.on("end", () => {
  try {
    let logs = [];
    const originalLog = console.log;

    // Capture console.log outputs
    console.log = (...args) => {
      logs.push(args.join(" "));
      originalLog.apply(console, args);
    };

    let result = eval(input);

    // Restore console.log
    console.log = originalLog;

    process.stdout.write(JSON.stringify({
      output: logs.join("\n") || (result !== undefined ? result.toString() : ""),
      error: "NO Error",
      success: true
    }));
  } catch (err) {
    process.stdout.write(JSON.stringify({
      output: "Please Check The Error Log",
      error: err.message,
      success: false
    }));
  }
});


