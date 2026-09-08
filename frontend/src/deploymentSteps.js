// Mirrors app/provisioning/fake_compute.py STEPS — kept in sync by hand
// since the frontend has no build-time link to the backend's step labels
// (env.status_detail is a free-text label the backend sends over the wire).
export const COMPUTE_STEPS = [
  'Allocating bare-metal capacity',
  'Provisioning Kubernetes control plane',
  'Bootstrapping worker nodes & GPU drivers',
  'Configuring container runtime & storage',
  'Establishing tenant network fabric',
  'Finalizing',
]

export const STEP_LOGS = [
  ['Querying available capacity at Datacenter-A…', 'Reserving bare-metal server(s)…', 'Capacity reserved.'],
  [
    'Bootstrapping etcd cluster…',
    'Starting kube-apiserver, kube-scheduler, kube-controller-manager…',
    'Control plane healthy (3/3 nodes ready).',
  ],
  [
    'Installing NVIDIA driver 550.90.07…',
    'Installing CUDA 12.4 runtime + NCCL 2.20…',
    'Joining worker nodes to cluster…',
    'GPU devices detected and schedulable.',
  ],
  ['Installing containerd runtime…', 'Provisioning local NVMe scratch volumes…', 'Storage mounted and verified.'],
  [
    'Requesting isolated VPC from Netris controller…',
    'Allocating VLAN segments (North-South, OOB-Management)…',
    'Waiting for Netris to confirm network state…',
  ],
  ['Running post-provision health checks…', 'Registering environment with monitoring agent…', 'Finalizing…'],
]

// -1 (env.status_detail not found among the labels above) means the fake
// compute animation has finished every step — see fake_compute.progress_at,
// which falls back to "Compute provisioning complete" once done. Network
// fabric confirmation is a separate, Netris-gated stage on top of this.
export function currentStepIndex(statusDetail) {
  return COMPUTE_STEPS.indexOf(statusDetail)
}
