interface EmptyStateProps {
  title?: string;
  message?: string;
  lastIngestion?: string | null;
  source?: string | null;
  action?: React.ReactNode;
}

export default function EmptyState({
  title = "No verified records yet",
  message = "No verified records ingested yet for this filter.",
  lastIngestion,
  source,
  action,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 py-10 text-center"
    >
      <p className="text-lg font-semibold text-gray-900">{title}</p>
      <p className="mt-2 text-sm text-gray-600">{message}</p>
      <p className="mt-2 text-sm text-gray-500">
        No verified records ingested yet for this filter — last ingestion:{" "}
        {lastIngestion ? new Date(lastIngestion).toLocaleString("en-US") : "unknown"}
        , source: {source ?? "none yet"}.
      </p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
