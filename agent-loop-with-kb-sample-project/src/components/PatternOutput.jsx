import { useState } from "react";

export default function PatternOutput({ text, errors }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (errors?.length) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 space-y-1">
        {errors.map((e, i) => (
          <p key={i} className="text-sm text-red-700">{e}</p>
        ))}
      </div>
    );
  }

  if (!text) return null;

  return (
    <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-stone-100 bg-stone-50">
        <p className="text-xs font-semibold uppercase tracking-widest text-stone-400">
          Pattern
        </p>
        <button
          onClick={handleCopy}
          className="text-xs font-medium text-stone-500 hover:text-stone-800 border border-stone-200 hover:border-stone-400 rounded-lg px-3 py-1.5 transition-colors bg-white"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      {/* Instructions */}
      <pre className="px-5 py-5 text-[13px] font-mono leading-relaxed text-stone-700 whitespace-pre-wrap overflow-x-auto">
        {text}
      </pre>
    </div>
  );
}
