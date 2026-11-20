// Private stdin/JSON-lines bridge for itf.py. Reuse one Sharp runtime per batch.
const fs = require("node:fs");
const path = require("node:path");

async function main() {
  const { pixelSnap } = require("./pixel_snap");
  const { files, options } = JSON.parse(fs.readFileSync(0, "utf8"));
  for (const { input, output } of files) {
    try {
      await fs.promises.mkdir(path.dirname(output), { recursive: true });
      const info = await pixelSnap(input, output, options);
      console.log(JSON.stringify({ input, output, ...info }));
    } catch (err) {
      throw new Error(`${input}: ${err.message}`);
    }
  }
}

main().catch(err => {
  console.error(err.message);
  if (err.code === "MODULE_NOT_FOUND" || err.message.includes('load the "sharp" module')) {
    console.error("Install the optional runtime from asset/: npm ci --prefix pipeline/pixel_snap");
  }
  process.exitCode = 1;
});
