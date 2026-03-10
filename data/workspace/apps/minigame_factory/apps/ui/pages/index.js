import { useState } from "react";

export default function Home() {
  const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const [projectId, setProjectId] = useState("");
  const [log, setLog] = useState("");

  async function createProject() {
    const r = await fetch(`${api}/projects`, { method: "POST" });
    const j = await r.json();
    setProjectId(j.project_id);
    setLog(JSON.stringify(j, null, 2));
  }

  async function submitSpec() {
    if (!projectId) return;
    const spec = {
      game_id: projectId,
      title: "Dungeon v2",
      genre: "dungeon",
      targets: { android: true, web_singlehtml: true },
      session: { length_sec: 180, difficulty: 2 },
      perspective: { allow_toggle: true, default: "fps", modes: ["fps", "topdown"] },
      controls: {
        android: { move: "virtual_joystick", look: "swipe", shoot: "tap", toggle_view: "button" },
        desktop: { move: "WASD", look: "mouse", shoot: "LMB", toggle_view: "V" }
      },
      build: {
        android: {
          package_name: "com.example.dungeonv2",
          version_name: "0.1.0",
          version_code: 1,
          export_format: ["apk_debug"]  // release is optional in v1.1
        },
        web: { single_file: true }
      }
    };

    const r = await fetch(`${api}/projects/${projectId}/spec`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec })
    });
    const j = await r.json();
    setLog(JSON.stringify(j, null, 2));
  }

  async function checkStatus() {
    if (!projectId) return;
    const r = await fetch(`${api}/projects/${projectId}`);
    const j = await r.json();
    setLog(JSON.stringify(j, null, 2));
  }

  return (
    <div style={{ padding: 20, fontFamily: "system-ui" }}>
      <h2>MiniGame Factory v1.1</h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={createProject}>1) Create Project</button>
        <button onClick={submitSpec} disabled={!projectId}>2) Submit Spec (enqueue)</button>
        <button onClick={checkStatus} disabled={!projectId}>3) Check Status</button>
      </div>
      <div style={{ marginTop: 12 }}>project_id: <b>{projectId || "-"}</b></div>
      <pre style={{ background: "#111", color: "#0f0", padding: 12, marginTop: 12, borderRadius: 8, overflow: "auto" }}>
{log}
      </pre>
      <p style={{ marginTop: 12, opacity: 0.8 }}>
        Artifacts will appear under <code>./output/&lt;project_id&gt;</code>.
      </p>
    </div>
  );
}
