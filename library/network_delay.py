#!/usr/bin/python

# Copyright: (c) 2021, Ho Kim <ho.kim@smartx.kr>
# MIT License
from __future__ import (absolute_import, division, print_function)
import ipaddress
import os
import subprocess
__metaclass__ = type

DOCUMENTATION = r'''
---
module: rook_ceph

short_description: Simple Network Delay Simulation Tool

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form '2.5.0' and not '2.4'.
version_added: '1.0.0'

description: Simple Network Delay Simulation Tool

options:
    network:
        description: Network configuration
        required: true
        type: dict
        suboptions:
            cidrV4:
                description: Network CIDRv4
                required: true
                type: str
            delay:
                description: Delay (ms)
                required: false
                type: int
                default: 0

author:
    - Ho Kim (@kerryeon)
'''

EXAMPLES = r'''
- name: Apply 100ms delay on an internal network plane
  kerryeon.ansible_network_delay.network_delay:
    apply:
      network:
        cidrV4: 172.20.0.0/16
        delay: 100
'''

RETURN = ''' # '''


def gather_facts():
    return {}


def apply(params: dict):
    # network
    network: dict = params['network']
    network_cidr_v4 = ipaddress.ip_network(network['cidrV4'])
    network_delay: int = int(network.get('delay') or 0)

    # detect interface
    ip_networks = [
        [
            token
            for token in line.split(' ')
            if token
        ]
        for line in subprocess.check_output([
            '/bin/bash', '-c', 'ip -br -4 a sh',
        ]).decode('utf-8').split('\n')[:-1]
    ]
    interface = next(
        name
        for [name, mode, ip_network] in ip_networks
        if mode == 'UP' and ipaddress.ip_network(ip_network, strict=False).subnet_of(network_cidr_v4)
    )

    contains_delay = any(
        'delay' in line
        for line in subprocess.check_output([
            '/bin/bash', '-c', f'tc qdisc show dev {interface}',
        ]).decode('utf-8').split('\n')[:-1]
    )

    # enable delay
    if network_delay > 0:
        mode = 'change' if contains_delay else 'add'

    # disable delay
    else:
        if not contains_delay:
            return False
        mode = 'del'

    # execute
    os.system(
        f'echo "tc qdisc {mode} dev {interface} root netem delay {network_delay}ms" > ~/output'
    )
    os.system(
        f'tc qdisc {mode} dev {interface} root netem delay {network_delay}ms'
    )

    # Finish
    return True


argument_spec = {
    'gather_facts': {'type': 'bool', 'required': False, },
    'apply': {'type': 'dict', 'required': False, },
}


def setup_module_object():
    from ansible.module_utils.basic import AnsibleModule
    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=False)

    return module


def run_task(module):
    ret = {'changed': False, 'failed': False, 'ansible_facts': {}}

    arg_gather_facts = module.params['gather_facts']
    if arg_gather_facts:
        ret['ansible_facts'] = gather_facts()
        return ret

    arg_apply = module.params['apply']
    if arg_apply:
        ret['changed'] = ret['changed'] or apply(arg_apply)
        return ret

    return ret


def main():
    module = setup_module_object()

    try:
        ret = run_task(module)
    except Exception as e:
        module.fail_json(msg='{0}: {1}'.format(type(e).__name__, str(e)))

    module.exit_json(**ret)


if __name__ == '__main__':
    main()
