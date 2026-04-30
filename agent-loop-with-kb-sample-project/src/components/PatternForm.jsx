import { useState } from "react";
import { PRESET_SIZES, PRESET_KEYS } from "../utils/presets.js";

export default function PatternForm({ onGenerate }) {
  const [stPer10, setStPer10]       = useState(20);
  const [rowPer10, setRowPer10]     = useState(28);
  const [sizeMode, setSizeMode]     = useState("preset"); // "preset" | "custom"
  const [presetKey, setPresetKey]   = useState("M");
  const [custom, setCustom]         = useState({ chest: 96, bodyLength: 42, sleeveLength: 50 });

  const handleSubmit = () => {
    const measurements = sizeMode === "preset" ? PRESET_SIZES[presetKey] : custom;
    onGenerate(
      { stPer10: Number(stPer10), rowPer10: Number(rowPer10) },
      measurements,
    );
  };

  const setCustomField = (key, val) =>
    setCustom((prev) => ({ ...prev, [key]: Number(val) }));

  return (
    <div className="space-y-6">

      {/* Pattern selector */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-stone-400 mb-3">
          Pattern
        </h2>
        <div className="border border-stone-200 rounded-xl px-4 py-3 bg-white flex items-center justify-between">
          <div>
            <p className="font-medium text-stone-800 text-sm">Raglan with Mock Neck</p>
            <p className="text-xs text-stone-400 mt-0.5">Bottom-up · in the round · seamless</p>
          </div>
          <span className="text-xs bg-stone-100 text-stone-500 px-2.5 py-1 rounded-full font-medium">
            v1
          </span>
        </div>
      </section>

      {/* Gauge */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-stone-400 mb-3">
          Gauge (per 10 cm, blocked swatch)
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-stone-500 font-medium">Stitches</span>
            <input
              type="number"
              value={stPer10}
              min={8} max={50} step={0.5}
              onChange={(e) => setStPer10(e.target.value)}
              className="border border-stone-200 rounded-lg px-3 h-10 text-sm bg-white focus:outline-none focus:border-stone-400 focus:ring-1 focus:ring-stone-300"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-stone-500 font-medium">Rows</span>
            <input
              type="number"
              value={rowPer10}
              min={8} max={80} step={0.5}
              onChange={(e) => setRowPer10(e.target.value)}
              className="border border-stone-200 rounded-lg px-3 h-10 text-sm bg-white focus:outline-none focus:border-stone-400 focus:ring-1 focus:ring-stone-300"
            />
          </label>
        </div>
      </section>

      {/* Size */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-stone-400 mb-3">
          Size
        </h2>

        {/* Mode toggle */}
        <div className="flex gap-2 mb-4">
          {["preset", "custom"].map((m) => (
            <button
              key={m}
              onClick={() => setSizeMode(m)}
              className={`text-xs font-medium px-4 py-2 rounded-lg border transition-colors ${
                sizeMode === m
                  ? "bg-stone-800 text-white border-stone-800"
                  : "bg-white text-stone-500 border-stone-200 hover:border-stone-400 hover:text-stone-700"
              }`}
            >
              {m === "preset" ? "Preset" : "Custom (cm)"}
            </button>
          ))}
        </div>

        {sizeMode === "preset" ? (
          <div>
            <div className="grid grid-cols-6 gap-2 mb-3">
              {PRESET_KEYS.map((key) => (
                <button
                  key={key}
                  onClick={() => setPresetKey(key)}
                  className={`h-10 rounded-lg border text-sm font-medium transition-colors ${
                    presetKey === key
                      ? "bg-stone-800 text-white border-stone-800"
                      : "bg-white text-stone-500 border-stone-200 hover:border-stone-400 hover:text-stone-700"
                  }`}
                >
                  {key}
                </button>
              ))}
            </div>
            <p className="text-xs text-stone-400">
              {PRESET_SIZES[presetKey].chest} cm chest ·{" "}
              {PRESET_SIZES[presetKey].bodyLength} cm body ·{" "}
              {PRESET_SIZES[presetKey].sleeveLength} cm sleeve
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            {[
              { key: "chest", label: "Chest circ." },
              { key: "bodyLength", label: "Body length" },
              { key: "sleeveLength", label: "Sleeve length" },
            ].map(({ key, label }) => (
              <label key={key} className="flex flex-col gap-1.5">
                <span className="text-xs text-stone-500 font-medium">{label}</span>
                <input
                  type="number"
                  value={custom[key]}
                  min={key === "chest" ? 60 : 20}
                  max={key === "chest" ? 200 : 80}
                  step={1}
                  onChange={(e) => setCustomField(key, e.target.value)}
                  className="border border-stone-200 rounded-lg px-3 h-10 text-sm bg-white focus:outline-none focus:border-stone-400 focus:ring-1 focus:ring-stone-300"
                />
              </label>
            ))}
          </div>
        )}
      </section>

      {/* Generate */}
      <button
        onClick={handleSubmit}
        className="w-full h-11 bg-stone-800 hover:bg-stone-700 active:scale-[0.99] text-white rounded-xl text-sm font-medium transition-all"
      >
        Generate Pattern
      </button>
    </div>
  );
}
