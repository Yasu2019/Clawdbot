import express from "express";
import bodyParser from "body-parser";
import fs from "fs";
import path from "path";

const OUTPUT_DIR = process.env.OUTPUT_DIR || "/workspace/output";
const TEMPLATES_DIR = process.env.TEMPLATES_DIR || "/workspace/templates";

const app = express();
app.use(bodyParser.json({ limit: "5mb" }));

app.get("/health", (_, res) => res.json({ ok: true }));

app.post("/build/singlehtml", (req, res) => {
  const { project_id, template_name, output_dir, spec } = req.body;
  const tplPath = path.join(TEMPLATES_DIR, template_name, "template_index.html");
  if (!fs.existsSync(tplPath)) return res.status(400).send("template_index.html not found");

  const tpl = fs.readFileSync(tplPath, "utf-8");

  const html = tpl
    .replaceAll("__TITLE__", spec?.title || "MiniGame")
    .replaceAll("__PROJECT_ID__", project_id || "unknown");

  const outDir = path.join(output_dir || path.join(OUTPUT_DIR, project_id), "web_singlehtml");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, "index.html"), html, "utf-8");

  res.json({ ok: true, outDir });
});

app.listen(8090, "0.0.0.0", () => console.log("node-builder listening on 8090"));
