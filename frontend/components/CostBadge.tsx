interface Props {
  tokens?: number;
  costUsd?: number;
}

export function CostBadge({ tokens = 0, costUsd = 0 }: Props) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full bg-white border border-slate-200 px-3 py-1 text-xs shadow-sm">
      <span className="text-slate-500">Usage</span>
      <span className="font-medium text-slate-700">
        {tokens.toLocaleString()} tokens
      </span>
      <span className="w-px h-3 bg-slate-200" />
      <span className="font-semibold text-emerald-700">
        ${costUsd.toFixed(5)}
      </span>
    </div>
  );
}
