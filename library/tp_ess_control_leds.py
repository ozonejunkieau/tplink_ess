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
        leds_enabled=dict(type='bool', required=True),
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
    _enable_led = module.params['leds_enabled']

    # Attempt to login and get config, should throw an exception if the password is wrong.
    with TPLinkSession(_host, _username, _password) as tps:        
        # Check the state of the switch
        led_config = tps.get_led_state()

    # Populate both `got` and `wanted`. ❷

    got = {'leds_enabled': led_config}
    wanted = {'leds_enabled': _enable_led}

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
        tps.set_led_state(_enable_led)

        led_config = tps.get_led_state()
    
    # Run an assertion that the desired changes have been applied.
    assert led_config == _enable_led

    module.exit_json(**result)


if __name__ == '__main__':
    main()