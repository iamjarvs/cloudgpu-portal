const STATUS_META = {
  queued: { label: 'Queued', className: 'pill-blue' },
  provisioning_compute: { label: 'Provisioning', className: 'pill-blue' },
  awaiting_network: { label: 'Finalizing network', className: 'pill-purple' },
  stalled: { label: 'Taking longer than expected', className: 'pill-amber' },
  active: { label: 'Active', className: 'pill-green' },
  failed: { label: 'Failed', className: 'pill-red' },
  deleting: { label: 'Terminating', className: 'pill-gray' },
  deleted: { label: 'Terminated', className: 'pill-gray' },
  delete_failed: { label: 'Delete failed', className: 'pill-red' },
}

export default function StatusPill({ status }) {
  const meta = STATUS_META[status] || { label: status, className: 'pill-gray' }
  return <span className={`status-pill ${meta.className}`}>{meta.label}</span>
}
