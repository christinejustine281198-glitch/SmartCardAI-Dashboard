let input = "";
process.stdin.setEncoding("utf-8");

process.stdin.on("data", chunk => input += chunk);

process.stdin.on("end", () => {
  let logs = [];
  const originalLog = console.log;
  console.log = (...args) => {
    logs.push(args.join(" "));
    originalLog.apply(console, args);
  };

  try {
    let result = eval(input); // Executes the input JS code

    console.log = originalLog; // Restore original console.log

    process.stdout.write(JSON.stringify({
      output: logs.join("\n") || (result !== undefined ? result.toString() : ""),
      error: "No error, script executed successfully",
      success: true
    }));
  } catch (err) {
    console.log = originalLog;

    process.stdout.write(JSON.stringify({
      output: logs.join("\n") || "please check the error log",
      error: err.message,
      success: false
    }));
  }
});


