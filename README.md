tp-link Easy Smart Switch Ansible Module
=========

This role facilitates configuring of tp-link Easy Smart Switches, particularly VLAN configuration.

Note: This is an early implementation that is _not_ exhaustively tested!

Compatible Devices
------------
At this time it has been tested against the following devices:
- TL-SG1016PE
- TL-SG108E

Requirements
------------

Currently this role has been tested only against Python 3.9. This will eventually be shifted back to Python 3.x, in order to maintain compatibility with supported Ansible Tower installations. 
_This will mostly relate to string formatting._

Python `requests` is required.

Role Variables
--------------

### VLAN Configuration
This role requires a lookup dictionary of VLAN's:

    vlan_lookup:
      default:
        name: DEFAULT1
        vlan: 1

      management:
        name: MANAGEMENT2
        vlan: 2

### Switch Variable Configuration
This role is designed to handle multiple switches, so the top level switch lookup structure is a list. The below demonstration is for an 8 port switch. **All ports must be specified in the configuration, partial specification is both untested and may result in unknown behaviour.**

    tp_link_switches: 
      - host: 192.0.2.10
        username: test_user
        password: test_password
        name: demo_switch
        vlan_enabled: yes
        leds_enabled: no
        port_configuration:
          - port: 1
            comment: switch uplink to core
            pvid: "{{ vlan_lookup.management }}"
            tagged:
              - "{{ vlan_lookup.management }}"
              - "{{ vlan_lookup.default }}"

          - port: 2
            pvid: "{{ vlan_lookup.default }}"
            untagged:
              - "{{ vlan_lookup.default }}"  

          - port: 3
            pvid: "{{ vlan_lookup.default }}"
            untagged:
              - "{{ vlan_lookup.default }}"    

          - port: 4
            pvid: "{{ vlan_lookup.default }}"
            untagged:
              - "{{ vlan_lookup.default }}"    

          - port: 5
            pvid: "{{ vlan_lookup.default }}"
            untagged:
              - "{{ vlan_lookup.default }}"           

          - port: 6
            pvid: "{{ vlan_lookup.default }}"
            untagged:
              - "{{ vlan_lookup.default }}"            

          - port: 7
            comment: Management Interface
            pvid: "{{ vlan_lookup.management }}"
            untagged:
              - "{{ vlan_lookup.management }}"            

          - port: 8
            comment: Dual VLAN interface
            pvid: "{{ vlan_lookup.management }}"
            untagged:
              - "{{ vlan_lookup.management }}"     
            tagged:
              - "{{ vlan_lookup.default }}"


Example Playbook
----------------

A complete switch configuration can be achieved by using the abovementioned variable structure and then executing the role as below:

    - hosts: localhost
      roles:
        - role: ozonejunkieau.tplink_ess
          tags: 
            - configure_switches
           

If more control is required, or only some aspects of configuration are desired, the custom libraries in the role can be used if the role is included without tags:

    - hosts: localhost
      roles:
        - role: ozonejunkieau.tplink_ess


## Library Usage

### Reliability Issues
The switches have generally been well behaved during the testing of this role. Issues that I have seen so far:
* Bizarre behaviour of the switch, with VLAN configuration not "sticking" after being applied.  A hard power reset solved this, a soft reset would not solve the problem.
* The web interface on the 1016PE seems to freeze occassionally, with timeouts on Port 80. I have found no pattern in these. The best I have come up with is to include the below:

      - name: "Wait for switch to respond, sometimes they are unresponsive..."
        wait_for: 
          host: 192.0.2.10
          port: 80
          timeout: 300

### Enable or Disable 802.1Q VLAN Support
    - name: Ensure that 802.1Q support is enabled on the switch
      tp_ess_control_vlans:
        host: 192.0.2.10
        username: admin
        password: admin
        vlan_8021q_enabled: yes
      delegate_to: localhost
      diff: yes
      run_once: yes

### Configuration Backup

The below pair of tasks download the switch configuration and dump it in base64 encoded format to the Ansible log output. Handy if you need to be able to roll back, will be much more useful once a `restore` task is also available.

    - name: Get a full backup of the switch configuration, base64 encoded.
      tp_ess_get_backup:
        host: 192.0.2.10
        username: admin
        password: admin
      delegate_to: localhost
      register: device_backup
      run_once: yes

    - debug: var=device_backup

### Single VLAN Configuration
Due to the way the interface and consequently the *"API"* works, the below task is used to configure a specific VLAN on the switch. This configuration includes all tagged port members, untagged port members and a list of ports that should have this VLAN as a PVID.

  - name: Set vlan config
    tp_ess_set_vlan:
      name: vlan_num_130
      vid: 130
      host: 192.0.2.10
      username: admin
      password: admin
      pvid_ports:
        - 5
      untagged_ports:
        - 5
      tagged_ports: 
        - 4
    delegate_to: localhost
    diff: yes
    run_once: yes

### LED Control
As mentioned, this allows all LED's to be disabled.

    - tp_ess_control_leds:
        host: 192.0.2.10
        username: admin
        password: admin
        leds_enabled: yes
      diff: yes
      run_once: yes
      delegate_to: localhost

### POE Configuration
For the POE supported switches, basic control of POE functionality is implemented. **At this time, no control is possible, this task only runs in check mode but will fail if a change is required.**
I may add further functionality to this if required, the main reason I have included it at the moment is to ensure that particular ports that require power are powered. No mode configuration is possible as yet.

    - tp_ess_set_poe:
        host: 192.0.2.10
        username: admin
        password: administrator
        poe_ports:
          - 1
          - 2
          - 3
          - 4
      diff: yes
      run_once: yes
      delegate_to: localhost
      check_mode: yes
           

License
-------

BSD

Author Information
------------------

Tristan Steele  
tristan.steele@gmail.com  
https://github.com/ozonejunkieau
