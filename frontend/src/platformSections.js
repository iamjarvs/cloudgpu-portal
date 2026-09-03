// Config for the sidebar's "platform" groups and the generic placeholder
// pages they route to. These are the parts of a real neocloud console
// (Compute, Networking, Storage...) that aren't implemented for the demo —
// they still route somewhere real and on-brand instead of a dead link.
export const PLATFORM_SECTIONS = {
  compute: {
    label: 'Compute',
    icon: 'cpu',
    description: 'Bare-metal and GPU instance management beyond dedicated environments.',
    children: [
      { slug: 'bare-metal', label: 'Bare Metal', blurb: 'Standalone bare-metal servers outside a provisioned environment.' },
      { slug: 'gpu-instances', label: 'GPU Instances', blurb: 'On-demand single-GPU and multi-GPU instances billed by the hour.' },
      { slug: 'kubernetes', label: 'Kubernetes', blurb: 'Managed Kubernetes clusters layered on top of your environments.' },
    ],
  },
  networking: {
    label: 'Networking',
    icon: 'network',
    description: 'VPCs, load balancers, and firewall policy across every environment.',
    children: [
      { slug: 'vpcs', label: 'VPCs', blurb: 'Virtual private clouds and peering between environments.' },
      { slug: 'load-balancers', label: 'Load Balancers', blurb: 'L4/L7 load balancing in front of your inference endpoints.' },
      { slug: 'firewalls', label: 'Firewalls', blurb: 'Security groups and ingress/egress firewall rules.' },
    ],
  },
  storage: {
    label: 'Storage',
    icon: 'database',
    description: 'Block and object storage volumes attached to your compute.',
    children: [
      { slug: 'block-storage', label: 'Block Storage', blurb: 'NVMe-backed block volumes for checkpoints and datasets.' },
      { slug: 'object-storage', label: 'Object Storage', blurb: 'S3-compatible object storage for model artifacts.' },
    ],
  },
  'data-services': {
    label: 'Data Services',
    icon: 'database',
    description: 'Managed data infrastructure for training and inference pipelines.',
    children: [
      { slug: 'managed-postgres', label: 'Managed Postgres', blurb: 'Fully managed Postgres for experiment tracking metadata.' },
      { slug: 'model-registry', label: 'Model Registry', blurb: 'Version and promote models across environments.' },
    ],
  },
  insights: {
    label: 'Insights',
    icon: 'barChart',
    description: 'Usage reporting, capacity forecasting, and alerting.',
    children: [
      { slug: 'usage-reports', label: 'Usage Reports', blurb: 'Historical GPU-hour and network utilization reporting.' },
      { slug: 'alerts', label: 'Alerts', blurb: 'Threshold-based alerting on utilization and health.' },
    ],
  },
  marketplace: {
    label: 'Marketplace',
    icon: 'shoppingBag',
    description: 'Container images and solution templates to deploy in one click.',
    children: [
      { slug: 'container-images', label: 'Container Images', blurb: 'Curated training and inference container images.' },
      { slug: 'solution-templates', label: 'Solution Templates', blurb: 'One-click reference architectures for common workloads.' },
    ],
  },
  security: {
    label: 'Security',
    icon: 'shield',
    description: 'Identity, access control, and audit trails.',
    children: [
      { slug: 'iam', label: 'IAM', blurb: 'Roles and permissions for teammates on this account.' },
      { slug: 'audit-log', label: 'Audit Log', blurb: 'A record of every control-plane action on your account.' },
    ],
  },
}
