// Run the code cells of JupyterLite notebooks in Pyodide, one runtime per notebook
// like a kernel, after installing a local pyevtgen wheel. Usage:
// node test_lite_notebooks.mjs <wheel> <notebook>...
import { readFileSync } from "node:fs";
import { basename } from "node:path";
import { loadPyodide } from "pyodide";

const [wheel, ...notebooks] = process.argv.slice(2);
for (const notebook of notebooks) {
  const pyodide = await loadPyodide({ stdout: () => {} });
  await pyodide.loadPackage("micropip");
  const target = `/tmp/${basename(wheel)}`;
  pyodide.FS.writeFile(target, readFileSync(wheel));
  await pyodide.runPythonAsync(`
import os
os.environ["MPLBACKEND"] = "Agg"
import micropip
await micropip.install("emfs:${target}")
`);
  const cells = JSON.parse(readFileSync(notebook, "utf8"))
    .cells.filter((cell) => cell.cell_type === "code")
    .map((cell) => [].concat(cell.source).join(""));
  for (const [index, source] of cells.entries()) {
    try {
      await pyodide.loadPackagesFromImports(source);
      await pyodide.runPythonAsync(source);
    } catch (error) {
      console.error(`${notebook}: code cell ${index + 1} failed`);
      throw error;
    }
  }
  const installed = pyodide.runPython(
    "from importlib.metadata import version; version('pyevtgen')",
  );
  if (
    !basename(wheel).startsWith(`pyevtgen-${installed.replace("+", "%2B")}-`) &&
    !basename(wheel).startsWith(`pyevtgen-${installed}-`)
  ) {
    throw new Error(
      `Notebook replaced the tested wheel with pyevtgen ${installed}`,
    );
  }
  console.log(`${notebook}: ${cells.length} code cells passed`);
}
