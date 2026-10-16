const STYLES: Record<string, string> = {
  scheduled: "bg-blue-100 text-blue-800",
  published: "bg-blue-100 text-blue-800",
  healthy: "bg-green-100 text-green-800",
  success: "bg-green-100 text-green-800",
  sold: "bg-gray-200 text-gray-800",
  held: "bg-gray-200 text-gray-800",
  postponed: "bg-yellow-100 text-yellow-800",
  degraded: "bg-yellow-100 text-yellow-800",
  partial_success: "bg-yellow-100 text-yellow-800",
  cancelled: "bg-red-100 text-red-800",
  down: "bg-red-100 text-red-800",
  failed: "bg-red-100 text-red-800",
  unknown: "bg-gray-100 text-gray-700",
  pending_license: "bg-purple-100 text-purple-800",
  PENDING_LICENSE: "bg-purple-100 text-purple-800",
  running: "bg-blue-100 text-blue-800",
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = STYLES[status] ?? STYLES.unknown;
  const label = status.replace(/_/g, " ");
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}
    >
      {label}
    </span>
  );
}
