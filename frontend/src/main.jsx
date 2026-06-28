import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Cuboid,
  FileArchive,
  FileAudio,
  Images,
  Moon,
  Music2,
  Palette,
  RefreshCw,
  Save,
  Search,
  Sun,
  Tags
} from "lucide-react";
import "./styles.css";

const RESOURCE_TABS = [
  { id: "model", label: "模型", icon: Cuboid },
  { id: "audio", label: "音效", icon: Music2 },
  { id: "image", label: "图片", icon: Images }
];

const PALETTES = [
  { id: "graphite", label: "Graphite" },
  { id: "atelier", label: "Atelier" },
  { id: "harbor", label: "Harbor" }
];

const THREE_MODEL_FORMATS = new Set(["glb", "gltf", "obj", "fbx"]);
const WAR3_MODEL_FORMATS = new Set(["mdx", "mdl"]);
const IMAGE_FORMATS = new Set(["png", "jpg", "jpeg", "webp"]);
const APP_BASE = new URL("./", window.location.href).pathname.replace(/\/$/, "");
const TEAM_COLOR_FALLBACK =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAClgGA7y4E4wAAAABJRU5ErkJggg==";
const TEAM_GLOW_FALLBACK =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAClgGA7y4E4wAAAABJRU5ErkJggg==";

function apiUrl(path) {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${APP_BASE}${normalized}` || normalized;
}

async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

function readStoredTheme() {
  const systemDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  return {
    scheme: localStorage.getItem("warvault-scheme") || (systemDark ? "dark" : "light"),
    palette: localStorage.getItem("warvault-palette") || "graphite"
  };
}

function applyTheme(scheme, palette) {
  document.documentElement.dataset.appScheme = scheme;
  document.documentElement.dataset.appSchemeGuard = scheme;
  document.documentElement.dataset.appStyle = palette;
  localStorage.setItem("warvault-scheme", scheme);
  localStorage.setItem("warvault-palette", palette);
}

const BOOT_THEME = readStoredTheme();
applyTheme(BOOT_THEME.scheme, BOOT_THEME.palette);

function formatBytes(value) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function App() {
  const [scheme, setScheme] = useState(BOOT_THEME.scheme);
  const [palette, setPalette] = useState(BOOT_THEME.palette);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [kind, setKind] = useState("model");
  const [assets, setAssets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    applyTheme(scheme, palette);
  }, [scheme, palette]);

  useEffect(() => {
    if (!paletteOpen) return undefined;
    function close(event) {
      if (!event.target.closest(".palette-menu-wrap")) setPaletteOpen(false);
    }
    window.addEventListener("pointerdown", close);
    return () => window.removeEventListener("pointerdown", close);
  }, [paletteOpen]);

  async function loadAssets(nextKind = kind) {
    const params = new URLSearchParams({ kind: nextKind, limit: "500" });
    if (query.trim()) params.set("q", query.trim());
    const data = await request(`/api/assets?${params.toString()}`);
    setAssets(data);
    setSelected((current) => {
      if (!current || current.kind !== nextKind) return data[0] || null;
      return data.find((asset) => asset.id === current.id) || data[0] || null;
    });
  }

  useEffect(() => {
    loadAssets().catch((error) => setMessage(error.message));
    const timer = window.setInterval(() => {
      loadAssets().catch(() => {});
    }, 15000);
    return () => window.clearInterval(timer);
  }, [kind]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadAssets().catch((error) => setMessage(error.message));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [query]);

  async function refresh() {
    setBusy(true);
    setMessage("");
    try {
      await loadAssets();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveAsset(asset) {
    const updated = await request(`/api/assets/${asset.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        tags: asset.tags,
        description: asset.description,
        favorite: asset.favorite
      })
    });
    setSelected(updated);
    setAssets((items) => items.map((item) => (item.id === updated.id ? updated : item)));
    setMessage("资源信息已保存");
  }

  const stats = useMemo(() => {
    const tagSet = new Set();
    let totalSize = 0;
    for (const asset of assets) {
      totalSize += asset.size || 0;
      for (const tag of asset.tags || []) tagSet.add(tag);
    }
    return { count: assets.length, tags: tagSet.size, totalSize };
  }, [assets]);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <nav className="nav-list" aria-label="资源类型">
          {RESOURCE_TABS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={kind === item.id ? "nav-item active" : "nav-item"}
                onClick={() => {
                  setKind(item.id);
                  setSelected(null);
                }}
                title={item.label}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="search-box">
            <Search size={18} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索文件名、路径、标签、描述" />
          </div>
          <div className="theme-controls">
            <button className="icon-button" onClick={() => setScheme(scheme === "dark" ? "light" : "dark")} title="切换明暗">
              {scheme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <div className="palette-menu-wrap">
              <button className="icon-button" onClick={() => setPaletteOpen((value) => !value)} title="主题">
                <Palette size={18} />
              </button>
              {paletteOpen && (
                <div className="palette-menu" role="menu">
                  {PALETTES.map((item) => (
                    <button
                      key={item.id}
                      className={palette === item.id ? "palette-option active" : "palette-option"}
                      onClick={() => {
                        setPalette(item.id);
                        setPaletteOpen(false);
                      }}
                      role="menuitem"
                    >
                      <span className={`palette-swatch ${item.id}`} />
                      <span>{item.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button className="icon-button" onClick={refresh} title="刷新列表" disabled={busy}>
              <RefreshCw className={busy ? "spin" : ""} size={18} />
            </button>
          </div>
        </header>

        {message && <div className="message">{message}</div>}

        <ResourcePage
          kind={kind}
          assets={assets}
          selected={selected}
          setSelected={setSelected}
          stats={stats}
          onSave={saveAsset}
        />
      </section>
    </main>
  );
}

function ResourcePage({ kind, assets, selected, setSelected, stats, onSave }) {
  const active = RESOURCE_TABS.find((item) => item.id === kind);
  const Icon = active.icon;
  return (
    <div className="resource-page">
      <section className="collection-panel">
        <div className="page-heading">
          <div className="heading-icon">
            <Icon size={20} />
          </div>
          <div>
            <h1>{active.label}</h1>
            <p>{stats.count} 个资源，{stats.tags} 个标签，{formatBytes(stats.totalSize)}</p>
          </div>
        </div>
        <div className={kind === "image" ? "asset-grid" : "asset-list"}>
          {assets.map((asset) => (
            <AssetCard key={asset.id} asset={asset} selected={selected?.id === asset.id} onSelect={() => setSelected(asset)} />
          ))}
          {assets.length === 0 && <div className="empty-state">还没有可显示的资源。后台会按配置源目录自动扫描。</div>}
        </div>
      </section>
      <AssetDetail asset={selected} onSave={onSave} />
    </div>
  );
}

function AssetCard({ asset, selected, onSelect }) {
  return (
    <button className={selected ? "asset-card selected" : "asset-card"} onClick={onSelect}>
      <Preview asset={asset} compact />
      <div className="asset-card-body">
        <div className="asset-name">{asset.name}</div>
        <div className="asset-meta">
          <span>{asset.format.toUpperCase()}</span>
          <span>{formatBytes(asset.size)}</span>
        </div>
        <TagLine tags={asset.tags} />
        <div className="asset-path">{asset.relative_path}</div>
      </div>
    </button>
  );
}

function Preview({ asset, compact = false }) {
  if (!asset) return <div className="preview-placeholder">选择资源</div>;
  if (asset.kind === "image") return <ImagePreview asset={asset} compact={compact} />;
  if (asset.kind === "audio") return <AudioPreview asset={asset} compact={compact} />;
  return <ModelPreview asset={asset} compact={compact} />;
}

function ImagePreview({ asset, compact }) {
  if (!IMAGE_FORMATS.has(asset.format)) {
    return (
      <div className={compact ? "thumb file-thumb" : "preview-frame file-preview"}>
        <Images size={compact ? 22 : 34} />
        <span>{asset.format.toUpperCase()}</span>
      </div>
    );
  }
  return (
    <div className={compact ? "thumb checker" : "preview-frame checker"}>
      <img src={apiUrl(asset.preview_url)} alt={asset.name} />
    </div>
  );
}

function AudioPreview({ asset, compact }) {
  return (
    <div className={compact ? "thumb audio-thumb" : "preview-frame audio-preview"}>
      <FileAudio size={compact ? 22 : 32} />
      {!compact && <audio src={apiUrl(asset.preview_url)} controls />}
    </div>
  );
}

function ModelPreview({ asset, compact }) {
  if (compact) {
    return (
      <div className="thumb model-thumb">
        <Cuboid size={24} />
        <span>{asset.format.toUpperCase()}</span>
      </div>
    );
  }
  if (WAR3_MODEL_FORMATS.has(asset.format)) return <War3ModelViewer asset={asset} />;
  if (!THREE_MODEL_FORMATS.has(asset.format)) {
    return (
      <div className="preview-frame model-fallback">
        <FileArchive size={34} />
        <strong>{asset.format.toUpperCase()} 模型</strong>
        <span>已入库。此格式暂无浏览器可视预览。</span>
      </div>
    );
  }
  return <ThreeModelViewer asset={asset} />;
}

function War3ModelViewer({ asset }) {
  const canvasRef = useRef(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    let disposed = false;
    let frame = 0;
    let viewer = null;
    let observer = null;
    const primaryPath = asset.relative_path || `${asset.name}.${asset.format}`;
    const primaryFile = primaryPath.split(/[\\/]/).pop();

    async function start() {
      setError("");
      const module = await import("mdx-m3-viewer");
      const ModelViewerPackage = module.default || module;
      if (disposed) return;

      const viewerApi = ModelViewerPackage.viewer || ModelViewerPackage.default?.viewer;
      if (!viewerApi?.ModelViewer || !viewerApi?.handlers?.mdx) {
        throw new Error("mdx-m3-viewer API is unavailable.");
      }

      viewer = new viewerApi.ModelViewer(canvas, { alpha: false, antialias: true });
      viewer.on?.("error", (event) => {
        console.warn("Warcraft model viewer error:", event);
      });

      const handlers = viewerApi.handlers;
      viewer.addHandler(handlers.mdx, resolveWar3Path, false);
      viewer.addHandler(handlers.blp);
      viewer.addHandler(handlers.tga);
      viewer.addHandler(handlers.dds);

      const scene = viewer.addScene();
      scene.camera.move([0, 0, 500]);
      scene.color[0] = 0.05;
      scene.color[1] = 0.07;
      scene.color[2] = 0.1;

      function resize() {
        const rect = canvas.getBoundingClientRect();
        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.max(320, Math.floor(rect.width * pixelRatio));
        canvas.height = Math.max(220, Math.floor(rect.height * pixelRatio));
        scene.viewport[2] = canvas.width;
        scene.viewport[3] = canvas.height;
      }

      function resolveWar3Path(path) {
        const normalized = String(path || "").replaceAll("\\", "/");
        const lowered = normalized.toLowerCase();
        if (lowered.startsWith("replaceabletextures/teamcolor/")) return TEAM_COLOR_FALLBACK;
        if (lowered.startsWith("replaceabletextures/teamglow/")) return TEAM_GLOW_FALLBACK;
        const normalizedPrimary = primaryPath.replaceAll("\\", "/");
        if (
          normalized === asset.name ||
          normalized === normalizedPrimary ||
          normalized.endsWith(`/${primaryFile}`) ||
          normalized.endsWith(`/${asset.name}.${asset.format}`)
        ) {
          return apiUrl(asset.preview_url);
        }
        const encodedPath = normalized
          .split("/")
          .filter(Boolean)
          .map((part) => encodeURIComponent(part))
          .join("/");
        return apiUrl(`/api/assets/${asset.id}/related/${encodedPath}`);
      }

      resize();
      observer = new ResizeObserver(resize);
      observer.observe(canvas);

      const model = await viewer.load(primaryPath, resolveWar3Path);
      if (!model || disposed) {
        setError("MDX/MDL 模型加载失败。");
        return;
      }
      const instance = model.addInstance();
      scene.addInstance(instance);
      if (instance.setSequenceLoopMode) instance.setSequenceLoopMode(2);
      if (instance.setSequence) instance.setSequence(0);

      function animate() {
        viewer.updateAndRender();
        frame = window.requestAnimationFrame(animate);
      }
      animate();
    }

    start().catch((reason) => {
      console.warn("Warcraft model viewer failed:", reason);
      if (!disposed) setError("Warcraft 模型预览组件加载失败。");
    });

    return () => {
      disposed = true;
      observer?.disconnect();
      window.cancelAnimationFrame(frame);
      try {
        viewer?.clear();
      } catch {
        // best-effort cleanup for third-party viewer
      }
    };
  }, [asset.id, asset.relative_path, asset.name, asset.format, asset.preview_url]);

  return (
    <div className="preview-frame war3-preview">
      <canvas ref={canvasRef} />
      {error && <div className="preview-error">{error}</div>}
    </div>
  );
}

function ThreeModelViewer({ asset }) {
  const mountRef = useRef(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    setError("");
    let cleanup = () => {};
    let frame = 0;
    let disposed = false;
    let observer = null;

    async function start() {
      const [THREE, { OrbitControls }, { GLTFLoader }, { OBJLoader }, { FBXLoader }] = await Promise.all([
        import("three"),
        import("three/examples/jsm/controls/OrbitControls.js"),
        import("three/examples/jsm/loaders/GLTFLoader.js"),
        import("three/examples/jsm/loaders/OBJLoader.js"),
        import("three/examples/jsm/loaders/FBXLoader.js")
      ]);
      if (disposed) return;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue("--preview-bg").trim() || "#111827");
      const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
      camera.position.set(2.4, 1.8, 2.8);
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      mount.appendChild(renderer.domElement);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      scene.add(new THREE.HemisphereLight(0xffffff, 0x4b5563, 2.4));
      const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
      keyLight.position.set(4, 6, 5);
      scene.add(keyLight);

      function resize() {
        const rect = mount.getBoundingClientRect();
        const width = Math.max(320, rect.width);
        const height = Math.max(220, rect.height);
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      }

      function fitObject(object) {
        const box = new THREE.Box3().setFromObject(object);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        object.position.sub(center);
        const maxAxis = Math.max(size.x, size.y, size.z) || 1;
        camera.position.set(maxAxis * 1.4, maxAxis * 1.05, maxAxis * 1.7);
        controls.target.set(0, 0, 0);
        controls.update();
      }

      function load() {
        const url = apiUrl(asset.preview_url);
        const onLoaded = (object) => {
          if (disposed) return;
          const model = object.scene || object;
          scene.add(model);
          fitObject(model);
        };
        const onError = () => setError("模型预览加载失败，文件仍可作为资源管理。");
        if (asset.format === "glb" || asset.format === "gltf") new GLTFLoader().load(url, onLoaded, undefined, onError);
        else if (asset.format === "obj") new OBJLoader().load(url, onLoaded, undefined, onError);
        else if (asset.format === "fbx") new FBXLoader().load(url, onLoaded, undefined, onError);
      }

      function animate() {
        controls.update();
        renderer.render(scene, camera);
        frame = window.requestAnimationFrame(animate);
      }

      resize();
      load();
      animate();
      observer = new ResizeObserver(resize);
      observer.observe(mount);
      cleanup = () => {
        controls.dispose();
        renderer.dispose();
        if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement);
      };
    }

    start().catch(() => setError("模型预览组件加载失败。"));

    return () => {
      disposed = true;
      observer?.disconnect();
      window.cancelAnimationFrame(frame);
      cleanup();
    };
  }, [asset.id]);

  return (
    <div className="preview-frame three-preview" ref={mountRef}>
      {error && <div className="preview-error">{error}</div>}
    </div>
  );
}

function AssetDetail({ asset, onSave }) {
  const [draft, setDraft] = useState(asset);
  useEffect(() => setDraft(asset), [asset]);

  if (!draft) return <aside className="detail-panel empty-detail">选择一个资源查看预览和元数据</aside>;

  const metadata = draft.metadata || {};
  const tagText = (draft.tags || []).join(", ");

  return (
    <aside className="detail-panel">
      <Preview asset={draft} />
      <div className="detail-heading">
        <div>
          <h2>{draft.name}</h2>
          <p>{draft.relative_path}</p>
        </div>
      </div>

      <dl className="metadata-list">
        <Meta label="来源" value={draft.source_name} />
        <Meta label="格式" value={draft.format.toUpperCase()} />
        <Meta label="大小" value={formatBytes(draft.size)} />
        {metadata.width && <Meta label="尺寸" value={`${metadata.width} x ${metadata.height}`} />}
        {metadata.duration && <Meta label="时长" value={`${metadata.duration}s`} />}
        {draft.error && <Meta label="错误" value={draft.error} />}
      </dl>

      <label className="field">
        <span><Tags size={14} /> 标签</span>
        <input
          value={tagText}
          onChange={(event) =>
            setDraft({
              ...draft,
              tags: event.target.value.split(",").map((item) => item.trim()).filter(Boolean)
            })
          }
          placeholder="unit/hero, race/undead"
        />
      </label>
      <label className="field">
        <span>描述</span>
        <textarea
          value={draft.description || ""}
          onChange={(event) => setDraft({ ...draft, description: event.target.value })}
          placeholder="记录用途、来源、适用场景"
        />
      </label>
      <button className="primary-button wide" onClick={() => onSave(draft)}>
        <Save size={18} />
        <span>保存</span>
      </button>
    </aside>
  );
}

function Meta({ label, value }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function TagLine({ tags }) {
  if (!tags?.length) return <div className="tag-line muted">未标注</div>;
  return (
    <div className="tag-line">
      {tags.slice(0, 3).map((tag) => (
        <span key={tag}>{tag}</span>
      ))}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
