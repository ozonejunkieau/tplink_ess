#! /usr/bin/python3

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tp_ess_common import TPLinkSession

def main():
    # Define options accepted by the module. ❶
    module_args = dict(
        host=dict(type='str', required=True),
        username=dict(type='str', default="admin"),
        password=dict(type='str', required=True, no_log=True),
        poe_ports=dict(type='list', default=[]),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False
    )

    # Setup the module params in an accessible way:
    _host = module.params['host']
    _username = module.params['username']
    _password = module.params['password']
    _poe_ports = module.params['poe_ports']

    # Attempt to login and get config, should throw an exception if the password is wrong.
    with TPLinkSession(_host, _username, _password) as tps:        
        # Check the state of the switch
        poe_details = tps.get_poe_config()

        poe_ports = [i + 1 for i, x in enumerate(poe_details['state']) if x ]


    # Populate both `got` and `wanted`. ❷

    got = {"poe_ports": poe_ports}
    # Remove the port number as it's not really part of the config, just a helper!


    wanted = {
        "poe_ports": _poe_ports,
    }

    if got != wanted:
        result['changed'] = True
        result['diff'] = dict(
            before=yaml.safe_dump(got),
            after=yaml.safe_dump(wanted)
        )

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    print("Setting POE is not currently supported by this module, but it can be inspected to ensure the configuration matches expecations.")

    result['failed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()