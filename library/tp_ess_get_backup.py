#! /usr/bin/python3

import yaml
from ansible.module_utils.basic import AnsibleModule
from tplink_easysmartswitch import TPLinkSession

def main():
    # Define options accepted by the module. ❶
    module_args = dict(
        host=dict(type='str', required=True),
        username=dict(type='str', default="admin"),
        password=dict(type='str', required=True, no_log=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    # Setup the module params in an accessible way:
    _host = module.params['host']
    _username = module.params['username']
    _password = module.params['password']

    # Attempt to login and get config, should throw an exception if the password is wrong.
    with TPLinkSession(_host, _username, _password) as tps:        
        # Check the state of the switch
        curr_backup = tps.get_backup()


    result = dict(
        config_backup=curr_backup,
        changed=False
    )


    module.exit_json(**result)


if __name__ == '__main__':
    main()