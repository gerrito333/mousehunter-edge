import confuse
from apns import APNs, Frame, Payload

config = confuse.Configuration('mousehunter-edge', __name__)
APNTOKEN = config['APNToken'].get(None)
CERTFILE = config['certfile'].get(None)
print(f'TOKEN:>{APNTOKEN}< CERT:{CERTFILE}')
def send_notification(message):
    if CERTFILE == None:
        print('No certfile configured.')
        return
    if APNTOKEN == None:
        print('No APN token configured.')
        return
    hub = APNs(use_sandbox=True, cert_file=CERTFILE, key_file=CERTFILE)
    # Send a notification to iOS device
    
    payload = Payload(alert=message, sound="default")
    print('here')
    res = hub.gateway_server.send_notification(APNTOKEN, payload)
    print(payload)
send_notification('xxx')
