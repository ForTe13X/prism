import { useEffect, useState } from "react";
import Cockpit from "./Cockpit";
import { fetchSpec, fetchSpecs } from "./api";
import type { Spec, SpecSummary } from "./types";

export default function App() {
  const [specs, setSpecs] = useState<SpecSummary[]>([]);
  const [specId, setSpecId] = useState<string>("");
  const [spec, setSpec] = useState<Spec | null>(null);
  const [error, setError] = useState<string>("");

  // load the catalogue once; default to the first domain
  useEffect(() => {
    fetchSpecs()
      .then((list) => {
        setSpecs(list);
        if (list[0]) setSpecId(list[0].id);
      })
      .catch((e) => setError(`无法连接后端(${e})。请先启动:uvicorn backend.app.main:app --port 8200`));
  }, []);

  // load the full spec whenever the selected domain changes
  useEffect(() => {
    if (!specId) return;
    setSpec(null);
    fetchSpec(specId).then(setSpec).catch((e) => setError(String(e)));
  }, [specId]);

  const accent = spec?.accent ?? "#3b82f6";

  return (
    <div className="pr-app" style={{ ["--accent" as string]: accent }}>
      <header className="pr-header">
        <div className="pr-brand">
          <span className="pr-logo">◣◥</span>
          <div>
            <h1>Prism</h1>
            <p className="pr-tagline">语义地基驱动的驾驶舱 · 整个界面是 spec 的纯函数</p>
          </div>
        </div>
        <label className="pr-domain">
          <span>领域</span>
          <select value={specId} onChange={(e) => setSpecId(e.target.value)}>
            {specs.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
      </header>

      {error && <div className="pr-banner pr-error">{error}</div>}

      {spec && (
        <>
          <div className="pr-banner">
            <strong>{spec.title}</strong>
            <span className="pr-muted">
              {" "}
              — {spec.description ?? ""} 切换上方「领域」即可零代码换一套驾驶舱({spec.entities.length} 实体 ·{" "}
              {spec.views.length} 视图)。
            </span>
          </div>
          <Cockpit spec={spec} />
          <footer className="pr-footer">
            Prism v{spec.version} · 数据为确定性合成(spec → 哈希种子,无随机)· 加一个 semantic_type
            只改 <code>widgets.tsx</code> 一处
          </footer>
        </>
      )}
    </div>
  );
}
