import { useEffect, useMemo, useState } from "react";
import { fetchData } from "./api";
import type { Entity, Row, Spec, View } from "./types";
import { renderWidget } from "./widgets";

function EntityCard({ entity, row }: { entity: Entity; row: Row }) {
  const idAttr = entity.attributes.find((a) => a.semantic_type === "identifier");
  const rest = entity.attributes.filter((a) => a !== idAttr);
  return (
    <div className="pr-card">
      <div className="pr-card-head">
        <span className="pr-card-icon">{entity.icon ?? "◆"}</span>
        <span className="pr-card-title">{idAttr ? String(row[idAttr.name]) : String(row._id)}</span>
      </div>
      <dl className="pr-card-body">
        {rest.map((attr) => (
          <div className="pr-field" key={attr.name}>
            <dt>{attr.label}</dt>
            <dd>{renderWidget(attr, row[attr.name])}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function EntityTable({ entity, rows }: { entity: Entity; rows: Row[] }) {
  return (
    <div className="pr-table-wrap">
      <table className="pr-table">
        <thead>
          <tr>
            {entity.attributes.map((a) => (
              <th key={a.name}>{a.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row._id)}>
              {entity.attributes.map((a) => (
                <td key={a.name}>{renderWidget(a, row[a.name])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ViewPanel({ spec, view }: { spec: Spec; view: View }) {
  const entity = useMemo(() => spec.entities.find((e) => e.type === view.entity), [spec, view]);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    setRows(null);
    setError("");
    fetchData(spec.id, view.entity)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, [spec.id, view.entity]);

  if (!entity) return <p className="pr-muted">spec 中无实体 “{view.entity}”。</p>;
  if (error) return <p className="pr-error">加载失败:{error}</p>;
  if (!rows) return <p className="pr-muted">加载中…</p>;

  return (
    <>
      <p className="pr-view-meta">
        {entity.icon} {entity.label} · {rows.length} 行 · 布局 <code>{view.layout}</code> · 控件由各属性的
        <code> semantic_type </code>自动决定
      </p>
      {view.layout === "table" ? (
        <EntityTable entity={entity} rows={rows} />
      ) : (
        <div className="pr-grid">
          {rows.map((row) => (
            <EntityCard key={String(row._id)} entity={entity} row={row} />
          ))}
        </div>
      )}
    </>
  );
}

export default function Cockpit({ spec }: { spec: Spec }) {
  const [activeId, setActiveId] = useState(spec.views[0]?.id);
  // reset to the first view whenever the domain (spec) changes
  useEffect(() => setActiveId(spec.views[0]?.id), [spec.id]);
  const view = spec.views.find((v) => v.id === activeId) ?? spec.views[0];

  return (
    <section className="pr-cockpit">
      <nav className="pr-tabs">
        {spec.views.map((v) => (
          <button
            key={v.id}
            className={v.id === view?.id ? "pr-tab is-active" : "pr-tab"}
            onClick={() => setActiveId(v.id)}
          >
            {v.title}
          </button>
        ))}
      </nav>
      {view ? <ViewPanel spec={spec} view={view} /> : <p className="pr-muted">该 spec 未定义视图。</p>}
    </section>
  );
}
