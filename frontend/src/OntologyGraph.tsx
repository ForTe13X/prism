import { useEffect, useMemo, useState } from "react";
import { fetchGraph } from "./api";
import { graphHeight, layoutGraph, statusValue } from "./graph";
import type { Entity, Graph, GraphNode, Spec } from "./types";
import { renderWidget, statusTone } from "./widgets";

const W = 760; // SVG coordinate width; scales to the container via viewBox

function NodeDetail({ entity, node }: { entity: Entity; node: GraphNode }) {
  const idAttr = entity.attributes.find((a) => a.semantic_type === "identifier");
  const rest = entity.attributes.filter((a) => a !== idAttr);
  return (
    <div className="pr-graph-detail">
      <div className="pr-card-head">
        <span className="pr-card-icon">{entity.icon ?? "◆"}</span>
        <span className="pr-card-title">{idAttr ? String(node.row[idAttr.name]) : node.id}</span>
      </div>
      <p className="pr-muted pr-graph-detail-type">{entity.label}</p>
      <dl className="pr-card-body">
        {rest.map((attr) => (
          <div className="pr-field" key={attr.name}>
            <dt>{attr.label}</dt>
            <dd>{renderWidget(attr, node.row[attr.name])}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export default function OntologyGraph({ spec, frame }: { spec: Spec; frame?: number }) {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  // reset the (potentially stale) graph + selection when the domain changes; keep the old graph on
  // mere frame changes so scrubbing recolours in place without a flash.
  useEffect(() => {
    setGraph(null);
    setError("");
    setSelected(null);
  }, [spec.id]);

  useEffect(() => {
    let cancelled = false;
    fetchGraph(spec.id, frame)
      .then((g) => {
        if (cancelled) return;
        setError("");
        setGraph(g);
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [spec.id, frame]);

  const typeOrder = useMemo(() => spec.entities.map((e) => e.type), [spec]);
  const entityByType = useMemo(
    () => new Map(spec.entities.map((e) => [e.type, e])),
    [spec],
  );

  const nodes = graph?.nodes ?? [];
  const height = graphHeight(nodes, typeOrder);
  const pos = useMemo(() => layoutGraph(nodes, typeOrder, { width: W, height, padX: 90, padY: 44 }), [
    nodes,
    typeOrder,
    height,
  ]);

  // tone per node, from its first status attribute (shared convention with the widget resolver)
  const toneOf = (n: GraphNode) => {
    const entity = entityByType.get(n.entity_type);
    const sv = entity ? statusValue(entity.attributes, n.row) : null;
    return sv == null ? "neutral" : statusTone(sv);
  };
  const labelOf = (n: GraphNode) => {
    const entity = entityByType.get(n.entity_type);
    const idAttr = entity?.attributes.find((a) => a.semantic_type === "identifier");
    return idAttr ? String(n.row[idAttr.name]) : n.id;
  };

  if (error) return <p className="pr-error">加载失败:{error}</p>;
  if (!graph) return <p className="pr-muted">加载中…</p>;

  const toneById = new Map(nodes.map((n) => [n.id, toneOf(n)]));
  const selectedNode = nodes.find((n) => n.id === selected) ?? null;
  const selectedEntity = selectedNode ? entityByType.get(selectedNode.entity_type) : null;
  const connected = new Set<string>();
  if (selected) {
    for (const e of graph.edges) {
      if (e.from === selected) connected.add(e.to);
      if (e.to === selected) connected.add(e.from);
    }
  }

  return (
    <>
      <p className="pr-view-meta">
        本体图谱 · {nodes.length} 节点 · {graph.edges.length} 边 · 节点由实体的 <code>status</code>{" "}
        上色,边由 <code>relations</code> 的确定性实例映射生成 · 拓扑跨帧稳定,拖 slider 看状态演化
      </p>
      <div className="pr-graph">
        <div className="pr-graph-canvas">
          <svg
            className="pr-graph-svg"
            viewBox={`0 0 ${W} ${height}`}
            role="img"
            aria-label="本体图谱"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <marker id="pr-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0,0 L8,4 L0,8 z" className="pr-arrow-head" />
              </marker>
            </defs>
            {/* edges first so nodes sit on top */}
            {graph.edges.map((e) => {
              const a = pos.get(e.from);
              const b = pos.get(e.to);
              if (!a || !b) return null;
              const touchesSel = selected != null && (e.from === selected || e.to === selected);
              const dim = selected != null && !touchesSel;
              const alert = toneById.get(e.from) === "bad" || toneById.get(e.to) === "bad";
              const cls = `pr-edge${alert ? " is-alert" : ""}${touchesSel ? " is-sel" : ""}${dim ? " is-dim" : ""}`;
              const mx = (a.x + b.x) / 2;
              return (
                <path
                  key={e.id}
                  className={cls}
                  d={`M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`}
                  markerEnd="url(#pr-arrow)"
                >
                  <title>{`${e.from} ${e.predicate} ${e.to}`}</title>
                </path>
              );
            })}
            {nodes.map((n) => {
              const p = pos.get(n.id);
              if (!p) return null;
              const tone = toneById.get(n.id);
              const isSel = n.id === selected;
              const dim = selected != null && !isSel && !connected.has(n.id);
              return (
                <g
                  key={n.id}
                  className={`pr-node tone-${tone}${isSel ? " is-sel" : ""}${dim ? " is-dim" : ""}`}
                  transform={`translate(${p.x} ${p.y})`}
                  onClick={() => setSelected(isSel ? null : n.id)}
                  data-node-id={n.id}
                  role="button"
                  tabIndex={0}
                >
                  <circle className="pr-node-dot" r={isSel ? 11 : 8} />
                  <text className="pr-node-label" x={13} y={4}>
                    {labelOf(n)}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
        <aside className="pr-graph-side">
          {selectedNode && selectedEntity ? (
            <NodeDetail entity={selectedEntity} node={selectedNode} />
          ) : (
            <div className="pr-graph-hint">
              <p className="pr-muted">点节点看详情(复用同一套控件)。</p>
              <ul className="pr-graph-legend">
                {spec.entities.map((e) => (
                  <li key={e.type}>
                    <span className="pr-legend-icon">{e.icon ?? "◆"}</span>
                    {e.label}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
