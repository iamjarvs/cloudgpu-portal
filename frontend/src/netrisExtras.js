// Field specs + prepopulated defaults for the four optional Netris add-on
// services (NAT, ACL, V-Net, Load Balancer) surfaced from the "+ Netris
// service" menu on both the New Environment page and an environment's
// detail page. Defaults mirror the shape of the real Netris v2 API bodies
// almost verbatim so the request built in the modal needs no translation —
// see app/provisioning/extras.py and app/netris/client.py on the backend.

export const EXTRA_KINDS = ['nat', 'acl', 'vnet', 'lb']

export const EXTRA_META = {
  nat: { label: 'NAT Rule', icon: 'globe', short: 'NAT' },
  acl: { label: 'ACL Rule', icon: 'shield', short: 'ACL' },
  vnet: { label: 'V-Net', icon: 'network', short: 'V-Net' },
  lb: { label: 'Load Balancer', icon: 'barChart', short: 'LB' },
}

function slug(name) {
  return (name || 'env').trim().replace(/[^a-zA-Z0-9-]+/g, '-').replace(/^-+|-+$/g, '') || 'env'
}

export function defaultConfig(kind, envName) {
  const base = slug(envName)
  switch (kind) {
    case 'nat':
      return {
        name: `${base}-AppRule`,
        state: 'enabled',
        action: 'DNAT',
        protocol: 'all',
        sourceAddress: '0.0.0.0/0',
        sourcePort: '1-65535',
        destinationAddress: '103.67.203.25/32',
        destinationPort: '',
        dnatToIP: '192.168.0.1/32',
        dnatToPort: '',
        comment: '',
        pool: true,
        portGroup: '',
      }
    case 'acl':
      return {
        name: `${base}-AllowHTTPS`,
        action: 'permit',
        proto: 'tcp',
        src_prefix: '0.0.0.0/0',
        dst_prefix: '',
        src_port_from: null,
        src_port_to: null,
        dst_port_from: 443,
        dst_port_to: 443,
        established: 1,
        reverse: 'yes',
        comment: '',
      }
    case 'vnet':
      return {
        name: `${base}-ExtraVNet`,
        vlan: 'auto',
        state: 'active',
        ipFamily: 'dual',
        gateways: [],
      }
    case 'lb':
      return {
        name: `${base}-LB`,
        description: '',
        protocol: 'TCP',
        ipFamily: 'IPv4',
        ip: '0.0.0.0',
        port: 443,
        status: 'enable',
        healthCheck: 'TCP',
        timeOut: 1000,
        requestPath: '',
        backend: [{ ip: '10.0.0.10', port: 8443, maintenance: false }],
      }
    default:
      return { name: base }
  }
}

export const FIELD_SPECS = {
  nat: [
    { key: 'name', label: 'Name', type: 'text' },
    { key: 'action', label: 'Action', type: 'select', options: ['DNAT', 'SNAT', 'ACCEPT_SNAT'] },
    { key: 'protocol', label: 'Protocol', type: 'select', options: ['all', 'tcp', 'udp', 'icmp'] },
    { key: 'sourceAddress', label: 'Source address', type: 'text' },
    { key: 'sourcePort', label: 'Source port', type: 'text' },
    { key: 'destinationAddress', label: 'Destination address', type: 'text' },
    { key: 'destinationPort', label: 'Destination port', type: 'text' },
    { key: 'dnatToIP', label: 'Forward to IP', type: 'text' },
    { key: 'dnatToPort', label: 'Forward to port', type: 'text' },
    { key: 'comment', label: 'Comment', type: 'text' },
  ],
  acl: [
    { key: 'name', label: 'Name', type: 'text' },
    { key: 'action', label: 'Action', type: 'select', options: ['permit', 'deny'] },
    { key: 'proto', label: 'Protocol', type: 'select', options: ['tcp', 'udp', 'icmp', 'all'] },
    { key: 'src_prefix', label: 'Source prefix', type: 'text' },
    {
      key: 'dst_prefix',
      label: 'Destination prefix',
      type: 'text',
      placeholder: "Leave blank to use this environment's own subnet",
    },
    { key: 'dst_port_from', label: 'Dest port from', type: 'number' },
    { key: 'dst_port_to', label: 'Dest port to', type: 'number' },
    { key: 'comment', label: 'Comment', type: 'text' },
  ],
  vnet: [
    { key: 'name', label: 'Name', type: 'text' },
    { key: 'vlan', label: 'VLAN', type: 'text' },
    { key: 'ipFamily', label: 'IP family', type: 'select', options: ['dual', 'ipv4', 'ipv6'] },
    { key: 'state', label: 'State', type: 'select', options: ['active', 'disabled'] },
  ],
  lb: [
    { key: 'name', label: 'Name', type: 'text' },
    { key: 'protocol', label: 'Protocol', type: 'select', options: ['TCP', 'UDP'] },
    { key: 'ip', label: 'Listener IP', type: 'text' },
    { key: 'port', label: 'Listener port', type: 'number' },
    { key: 'healthCheck', label: 'Health check', type: 'select', options: ['None', 'TCP', 'HTTP'] },
    { key: 'description', label: 'Description', type: 'text' },
  ],
}

export function summarize(kind, config) {
  if (!config) return ''
  switch (kind) {
    case 'nat':
      return `${config.action} ${config.protocol} ${config.destinationAddress || ''} → ${config.dnatToIP || ''}`
    case 'acl':
      return `${config.action} ${config.proto} ${config.src_prefix} → ${config.dst_prefix || "(this env's subnet)"}${config.dst_port_from ? ':' + config.dst_port_from : ''}`
    case 'vnet':
      return `VLAN ${config.vlan}, ${config.ipFamily}`
    case 'lb':
      return `${config.protocol} ${config.ip}:${config.port}`
    default:
      return ''
  }
}
