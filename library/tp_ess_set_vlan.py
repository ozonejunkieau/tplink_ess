
    #   pvid_ports:
    #     - 5
    #   untagged_ports:
    #     - 5
    #   tagged_ports: 
    #     - 4


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
        name=dict(type='str', required=True),
        vid=dict(type='int', required=True),
        pvid_ports=dict(type='list', default=[]),
        untagged_ports=dict(type='list', default=[]),
        tagged_ports=dict(type='list', default=[]),
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
    _vlan_name = module.params['name']
    _vlan_vid = module.params['vid']
    _pvid_ports = module.params['pvid_ports']
    _untagged_ports = module.params['untagged_ports']
    _tagged_ports = module.params['tagged_ports']


    # The VID is the bit that everything is indexed from...

    


    # Attempt to login and get config, should throw an exception if the password is wrong.
    with TPLinkSession(_host, _username, _password) as tps:        
        # Check the state of the switch
        vlan_details = tps.get_vlan_config_by_vid(vid=_vlan_vid)



    # Populate both `got` and `wanted`. ❷

    got = {**vlan_details}
    # Remove the port number as it's not really part of the config, just a helper!


    wanted = {
        "vid": _vlan_vid,
        "name": _vlan_name,
        "pvid_ports": _pvid_ports,
        "tagged_ports": _tagged_ports,
        "untagged_ports": _untagged_ports,
    }

    if got != wanted:
        result['changed'] = True
        result['diff'] = dict(
            before=yaml.safe_dump(got),
            after=yaml.safe_dump(wanted)
        )

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    # Apply changes. ❸
    with TPLinkSession(_host, _username, _password) as tps:

        # If the name doesn't match, the tag list or the untag list don't match: update main vlan page
        if got['name'] != wanted['name'] or got['tagged_ports'] != wanted['tagged_ports'] or got['untagged_ports'] != wanted['untagged_ports']:
            # Updated the port configuration
            tps.set_vlan_config_by_vid(_vlan_vid, wanted['name'], vlan_details['num_ports'], wanted['tagged_ports'], wanted['untagged_ports'])

        # If the pvid list doesn't match, update the pvid page
        if got['pvid_ports'] != wanted['pvid_ports']:
            # Updated the pvid configuration
            tps.set_pvid_config_by_vid(_vlan_vid, wanted['pvid_ports'])
    
    # Run an assertion that the desired changes have been applied.
    # assert curr_config[tp_ess_common.TPLINK_VID_STATE] == _enable_vlan

    module.exit_json(**result)


if __name__ == '__main__':
    main()