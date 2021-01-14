#!/usr/bin/python3
from os import terminal_size
import requests
from base64 import b64encode

# These field mappings are to allow decoding of the headers in the TP Link Web UI, 
# they are mostly generic but have only been populated with what I have required.
TPLINK_VID_STATE = 'state'

FIELD_MAPPING = {
    "qvlan_ds": [
        ('state', bool, None),
        ('portNum', int, None),
        ('vids', list, int),
        ('count', int, None),
        ('maxVids', int, None),
        ('names', list, str),
        ('tagMbrs', list, int),
        ('untagMbrs', list, int),
    ],
    "info_ds": [
        ("descriStr", list, str),
        ("macStr", list, str),
        ("ipStr", list, str),
        ("netmaskStr", list, str),
    ],
    "pvid_ds": [
        ("pvids", list, int)
    ],
    "portConfig": [
        ("state", list, int),
        ("priority", list, int),
        ("powerlimit", list, int),
        ("power", list, int),
        ("current", list, int),
        ("voltage", list, int),
        ("pdclass", list, int),
        ("powerstatus", list, int),
    ],
    "globalConfig": [
        ("system_power_limit", int, None),
        ("system_power_limit_min", int, None),
        ("system_power_limit_max", int, None),
        ("system_power_consumption", int, None),
    ]
}


def decode_fields(source_str: str, resp_type):
    """ This is the lower level decode of fields, no automatic guess of type is performed."""

    field_decoding = FIELD_MAPPING[resp_type]

    unpacked_fields = {}

    for field_name, field_type, field_subtype in field_decoding:
        search_term = f"{field_name}:".encode()
        field_location = source_str.find(search_term)
        assert field_location >= 0

        # Attempt to extract the value
        field_value_start = field_location + len(search_term) 
        if field_type is list:
            # Handle as a list
            field_value_end = source_str.find(b']', field_value_start)
            assert field_value_end > field_value_start
            list_str = source_str[field_value_start + 1:field_value_end].strip()

            if len(list_str) == 0:
                field_list = []
            else:
                if field_subtype is int:
                    list_base = 16 if b'x' in list_str else 10
                    field_list = [int(x,list_base) for x in list_str.split(b',')]
                elif field_subtype is str:
                    field_list = [x.replace(b"'", b"").replace(b'"',b"").decode() for x in list_str.split(b',')]

            unpacked_fields[field_name] = field_list

        else: 
            # Handle as a single value
            field_value_end = source_str.find(b',', field_value_start)
            assert field_value_end > field_value_start
            if field_type is not bool:
                field_value = field_type(source_str[field_value_start:field_value_end])
            else:
                field_value = source_str[field_value_start:field_value_end] == b'1'

            unpacked_fields[field_name] = field_value

    return unpacked_fields


def get_field_values(source_str: str):
    """ A somewhat general purpose code block for parsing the script headers of the HTML UI, will attempt to decode automatically based on looking for patterns."""

    # Iterate through all known responses and attempt to match a decode
    for resp_type in FIELD_MAPPING.keys():

        if f"var {resp_type}".encode() in source_str:
            # We have a match!
            return decode_fields(source_str, resp_type)

def get_field_values_poe(source_str: str):
    """ A somewhat general purpose code block for parsing the script headers of the HTML UI, will attempt to decode automatically based on looking for patterns."""
    all_fields = {}

    resp1 = "portConfig"
    all_fields.update(decode_fields(source_str, resp1))
    
    resp2 = "globalConfig"
    all_fields.update(decode_fields(source_str, resp2))
    
    return all_fields
    

def tplink_build_url(host, path):
    """ A helper function to build URL's for the device """
    return f"http://{host}/{path}"



def tplink_post(url: str):
    """ Issue a POST to the device. The Content-Type header seems to be required by some devices."""

    _response = requests.post(url, timeout=5, headers={"Content-Type":"application/x-www-form-urlencoded",})
    _response.raise_for_status() 

    return _response


def tplink_get(url: str):
    """ Issue a GET to the device."""
    _response = requests.get(url, timeout=5)
    _response.raise_for_status() 

    return _response

def tplink_get_and_attempt_parse(url: str):
    return get_field_values(tplink_get(url).content)

def tplink_login(host, username, password):
    """ Perform a login to the host. """
    login_url = tplink_build_url(host, f"logon.cgi?username={username}&password={password}&cpassword=&logon=Login")
    login_response = tplink_post(login_url)
    
    # This is a rough and ready approach for ensuring no errors ocurred during the auth process.
    if b"var logonInfo = new Array(\n0,\n0,0)" not in login_response.content:
        raise Exception("Invalid password or other authentication error.")
    else:
        return True

def tplink_logout(host):
    logout_url = tplink_build_url(host,"Logout.htm")
    tplink_get(logout_url)
    # There does not appear to be any way to test this has ocurred. The device is barely secure anyway and will time out quickly.

    return True

class TPLinkSession:
    def __init__(self, host, username, password) -> None:
        self._host = host
        self._user = username
        self._pass = password

    def __enter__(self):
        tplink_login(self._host, self._user, self._pass)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        tplink_logout(self._host)

    def build_url(self, url_path):
        return tplink_build_url(self._host, url_path)

    def get_vlan_config(self):
        vlan_url = self.build_url("Vlan8021QRpm.htm")
        return tplink_get_and_attempt_parse(vlan_url)

    def get_vlan_config_by_vid(self, vid: int):
        vlan_config = self.get_vlan_config()
        num_ports = vlan_config['portNum']

        if vlan_config['state'] is False:
            Exception("VLAN's must be enabled on the device first.")

        # If the VID is not in this response, it doesn't exist.
        try:
            vid_index = vlan_config['vids'].index(vid)
        except ValueError:
            return {
                "vid": vid,
                "name": "",
                "pvid_ports": [],
                "tagged_ports": [],
                "untagged_ports": [],
                "num_ports": num_ports,
            }

        pvid_config = self.get_pvid_config()

        def mask_to_ports(mask: int, port_count: int):
            return [x+1 for x in range(port_count) if mask >> x & 0b1]

        def list_to_ports(_list: list, port_match: int):
            return [i+1 for i, x in enumerate(_list) if x == port_match]

        tagged_port_mask = vlan_config['tagMbrs'][vid_index]
        untagged_port_mask = vlan_config['untagMbrs'][vid_index]

        result = {
                "vid": vid,
                "name": vlan_config['names'][vid_index],
                "pvid_ports": list_to_ports(pvid_config['pvids'], vid),
                "tagged_ports": mask_to_ports(tagged_port_mask, num_ports),
                "untagged_ports": mask_to_ports(untagged_port_mask, num_ports),
            }

        return result

    def set_vlan_config_by_vid(self, vid: int, name: str, num_ports: int, tagged_ports: list, untagged_ports: list):

        if len(set(tagged_ports).intersection(set(untagged_ports))) > 0:
            raise Exception("A port can not be both tagged and untagged.")

        PORT_UNTAGGED = 0
        PORT_TAGGED = 1
        PORT_NOT_MEMBER = 2

        port_tagging = []
        for p in range(1, num_ports + 1):
            if p in untagged_ports:
                this_port = PORT_UNTAGGED
            elif p in tagged_ports:
                this_port = PORT_TAGGED
            else:
                this_port = PORT_NOT_MEMBER

            port_tagging.append(this_port)

        selType_list = [f'selType_{i+1}={p}' for i,p in enumerate(port_tagging)]
        vlan_set_url = self.build_url(f"qvlanSet.cgi?vid={vid}&vname={name}&{'&'.join(selType_list)}&qvlan_add=Add%2FModify")
        tplink_get(vlan_set_url)

    def get_pvid_config(self):
        pvid_url = self.build_url("Vlan8021QPvidRpm.htm")
        return tplink_get_and_attempt_parse(pvid_url) 

    def set_pvid_config_by_vid(self, vid: int, pvid_ports: list):
        # Updated the pvid configuration
        pbm = sum([2**(i-1) for i in pvid_ports])
        
        pvid_set_url = self.build_url(f"vlanPvidSet.cgi?pbm={pbm}&pvid={vid}")
        tplink_get(pvid_set_url)

    def get_info(self):
        info_url = self.build_url("SystemInfoRpm.htm")
        return tplink_get_and_attempt_parse(info_url)

    def get_backup(self):
        backup_url = self.build_url("config_back.cgi")
        content = tplink_get(backup_url).content
        return b64encode(content)

    def set_vlan_state(self, vlan_state: bool):
        enable_8021q_vlan_url = self.build_url("qvlanSet.cgi?qvlan_en=1&qvlan_mode=Apply")
        disable_8021q_vlan_url = self.build_url("qvlanSet.cgi?qvlan_en=0&qvlan_mode=Apply")

        if vlan_state is True:
            tplink_get(enable_8021q_vlan_url)
        else:
            tplink_get(disable_8021q_vlan_url)

    def get_led_state(self):
        led_url = self.build_url("TurnOnLEDRpm.htm")
        led_content = tplink_get(led_url).content

        if b"var led = 0" in led_content:
            return False
        elif b"var led = 1" in led_content:
            return True
        
        raise Exception("Unexpected response whilst querying LED state on switch.")


    def set_led_state(self, led_state: bool):
        disabled_led_url = self.build_url("led_on_set.cgi?rd_led=0&led_cfg=Apply")
        enable_led_url = self.build_url("led_on_set.cgi?rd_led=1&led_cfg=Apply")

        if led_state is True:
            tplink_get(enable_led_url)
        else:
            tplink_get(disabled_led_url)

    def get_poe_config(self):
        poe_url = self.build_url("PoeConfigRpm.htm")
        poe_content = tplink_get(poe_url).content
        poe_config = get_field_values_poe(poe_content)
        return poe_config

    