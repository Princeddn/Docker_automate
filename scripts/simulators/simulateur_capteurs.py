"""
================================================================
  SIMULATEUR LORAWAN COMPLET — gRPC EDITION (CHIRPSTACK API)
================================================================
"""

import sys
import os
import struct
import time
import random
import json
import hashlib
import base64
import datetime

# ── Vérification dépendances ──
try:
    from Crypto.Cipher import AES
    from Crypto.Hash import CMAC
except ImportError:
    print("❌ Module 'pycryptodome' manquant ! (pip install pycryptodome)")
    sys.exit(1)

import paho.mqtt.client as mqtt
import grpc
from chirpstack_api import api, common

# ================================================================
# CONFIGURATION
# ================================================================
BROKER_IP       = "192.168.3.100"
BROKER_PORT     = 1883
MQTT_USER       = "chirpstack"
MQTT_PASS = os.getenv("MQTT_PASS")

# Port 8080 est le port gRPC par défaut sur ChirpStack v4
GRPC_SERVER     = f"{BROKER_IP}:8081"
API_KEY = os.getenv("CHIRPSTACK_API_KEY")

TENANT_ID       = "" # Sera auto-détecté
APPLICATION_ID  = "YOUR_APPLICATION_ID"
GATEWAY_ID      = "YOUR_GATEWAY_ID"

NB_CAPTEURS     = 10        
INTERVAL_SEC    = 0.5       
FPORT           = 1         

# ================================================================
# CODEC JAVASCRIPT
# ================================================================
CODEC_JS = """
function decodeUplink(input) {
    var bytes = input.bytes;
    if (bytes.length < 6) return { data: { error: "payload trop court" } };
    var temp = (bytes[0] << 8) | bytes[1];
    if (temp > 32767) temp -= 65536;
    return {
        data: {
            temperature: temp / 10.0,
            humidity: ((bytes[2] << 8) | bytes[3]) / 10.0,
            co2: (bytes[4] << 8) | bytes[5]
        }
    };
}
function encodeDownlink(input) { return { bytes: [], fPort: 1 }; }
"""

# ================================================================
# CRYPTOGRAPHIE LORAWAN (AES-128)
# ================================================================
def lorawan_encrypt(key, dev_addr, fcnt, direction, payload):
    k = len(payload)
    if k == 0: return b''
    n_blocks = (k + 15) // 16
    s = b''
    for i in range(1, n_blocks + 1):
        a = bytes([0x01, 0x00, 0x00, 0x00, 0x00, direction])
        a += struct.pack('<I', dev_addr)
        a += struct.pack('<I', fcnt)
        a += bytes([0x00, i])
        s += AES.new(key, AES.MODE_ECB).encrypt(a)
    return bytes(a ^ b for a, b in zip(payload, s[:k]))

def lorawan_mic(key, dev_addr, fcnt, direction, msg):
    b0 = bytes([0x49, 0x00, 0x00, 0x00, 0x00, direction])
    b0 += struct.pack('<I', dev_addr)
    b0 += struct.pack('<I', fcnt)
    b0 += bytes([0x00, len(msg)])
    h = CMAC.new(key, ciphermod=AES)
    h.update(b0 + msg)
    return h.digest()[:4]

def build_phy_payload(dev_addr, nwk_s_key, app_s_key, fcnt, fport, frm_payload):
    mhdr = bytes([0x40])
    fhdr = struct.pack('<IBH', dev_addr, 0x00, fcnt & 0xFFFF)
    enc_payload = lorawan_encrypt(app_s_key, dev_addr, fcnt, 0, frm_payload)
    msg = mhdr + fhdr + bytes([fport]) + enc_payload
    mic = lorawan_mic(nwk_s_key, dev_addr, fcnt, 0, msg)
    return msg + mic

# ================================================================
# ENCODAGE PROTOBUF OFFICIEL (Passerelle -> ChirpStack)
# ================================================================
from chirpstack_api import gw

def build_uplink_frame_protobuf(phy_payload, rssi=-80, snr=8.5):
    """Construit un UplinkFrame parfait en utilisant la librairie officielle gw"""
    frame = gw.UplinkFrame()
    
    frame.phy_payload = phy_payload
    
    # tx_info
    frame.tx_info.frequency = 868100000
    frame.tx_info.modulation.lora.bandwidth = 125000
    frame.tx_info.modulation.lora.spreading_factor = 7
    frame.tx_info.modulation.lora.code_rate = gw.CodeRate.CR_4_5
    
    # rx_info
    rx_info = frame.rx_info.add()
    rx_info.gateway_id = GATEWAY_ID
    rx_info.uplink_id = random.randint(1, 65535)
    rx_info.rssi = rssi
    rx_info.snr = snr
    rx_info.context = os.urandom(4)
    rx_info.crc_status = gw.CRCStatus.CRC_OK
    
    # Retourne le binaire Protobuf
    return frame.SerializeToString()

# ================================================================
# API gRPC CHIRPSTACK
# ================================================================
def get_grpc_channel():
    return grpc.insecure_channel(GRPC_SERVER)

def get_auth_token():
    return [("authorization", f"Bearer {API_KEY}")]

def get_tenant_from_app():
    global TENANT_ID
    channel = get_grpc_channel()
    client = api.ApplicationServiceStub(channel)
    try:
        req = api.GetApplicationRequest(id=APPLICATION_ID)
        resp = client.Get(req, metadata=get_auth_token())
        TENANT_ID = resp.application.tenant_id
        print(f"  ✅ Tenant ID récupéré (gRPC) : {TENANT_ID}")
        return True
    except grpc.RpcError as e:
        print(f"  ❌ Erreur gRPC Application : {e.details()}")
        return False

def get_or_create_profile():
    channel = get_grpc_channel()
    client = api.DeviceProfileServiceStub(channel)
    token = get_auth_token()
    try:
        req = api.ListDeviceProfilesRequest(tenant_id=TENANT_ID, limit=50)
        resp = client.List(req, metadata=token)
        for p in resp.result:
            if p.name == "Simulated-ABP":
                print(f"  ℹ️ Device Profile trouvé (gRPC) : {p.id}")
                return p.id
                
        req_c = api.CreateDeviceProfileRequest()
        req_c.device_profile.tenant_id = TENANT_ID
        req_c.device_profile.name = "Simulated-ABP"
        req_c.device_profile.region = common.Region.EU868
        req_c.device_profile.mac_version = common.MacVersion.LORAWAN_1_0_3
        req_c.device_profile.reg_params_revision = common.RegParamsRevision.RP002_1_0_3
        req_c.device_profile.supports_otaa = False
        req_c.device_profile.payload_codec_runtime = api.CodecRuntime.JS
        req_c.device_profile.payload_codec_script = CODEC_JS
        
        resp_c = client.Create(req_c, metadata=token)
        print(f"  ✅ Device Profile créé (gRPC) : {resp_c.id}")
        return resp_c.id
    except grpc.RpcError as e:
        print(f"  ❌ Erreur gRPC Profil : {e.details()}")
        return None

def create_devices(dp_id):
    channel = get_grpc_channel()
    client = api.DeviceServiceStub(channel)
    token = get_auth_token()
    devices = []
    
    for i in range(1, NB_CAPTEURS + 1):
        dev_eui = f"aa00000000{i:06x}"
        dev_addr = 0x01FF0000 + i
        name = f"Sim-Capteur-{i:04d}"
        seed = hashlib.sha256(dev_eui.encode()).digest()
        nwk_s_key = seed[:16]
        app_s_key = seed[16:32]
        
        try:
            req = api.CreateDeviceRequest()
            req.device.dev_eui = dev_eui
            req.device.name = name
            req.device.application_id = APPLICATION_ID
            req.device.device_profile_id = dp_id
            req.device.is_disabled = False
            req.device.skip_fcnt_check = True
            client.Create(req, metadata=token)
        except grpc.RpcError as e:
            if "already exists" not in e.details().lower():
                print(f"  ❌ {name} création error : {e.details()}")
        
        try:
            req_act = api.ActivateDeviceRequest()
            req_act.device_activation.dev_eui = dev_eui
            req_act.device_activation.dev_addr = f"{dev_addr:08x}"
            req_act.device_activation.app_s_key = app_s_key.hex()
            req_act.device_activation.nwk_s_enc_key = nwk_s_key.hex()
            req_act.device_activation.f_nwk_s_int_key = nwk_s_key.hex()
            req_act.device_activation.s_nwk_s_int_key = nwk_s_key.hex()
            req_act.device_activation.f_cnt_up = 0
            req_act.device_activation.n_f_cnt_down = 0
            client.Activate(req_act, metadata=token)
        except grpc.RpcError as e:
            print(f"  ❌ {name} ABP activation error: {e.details()}")

        devices.append({
            "dev_eui": dev_eui, "dev_addr": dev_addr,
            "nwk_s_key": nwk_s_key, "app_s_key": app_s_key,
            "name": name, "fcnt": 0,
            "temp_base": round(random.uniform(18.0, 24.0), 1),
            "hum_base": round(random.uniform(40.0, 60.0), 1),
        })
        
        if i % 3 == 0 or i == NB_CAPTEURS:
            print(f"  📡 {i}/{NB_CAPTEURS} capteurs prêts (gRPC)")
    return devices

# ================================================================
# VÉRIFICATION
# ================================================================
trames_recues = 0
def on_verification_msg(client, userdata, msg):
    global trames_recues
    trames_recues += 1
    try:
        data = json.loads(msg.payload)
        dev = data.get("deviceInfo", {}).get("deviceName", "?")
        obj = data.get("object", {})
        if trames_recues <= 5:
            print(f"  ✅ CHIRPSTACK → {dev} : {obj}")
    except: pass

def encode_sensor_payload(t, h, c):
    return struct.pack('>hHH', int(t * 10), int(h * 10), int(c))

# ================================================================
def main():
    global trames_recues
    print("=" * 64)
    print("  📡  SIMULATEUR LORAWAN COMPLET — gRPC EDITION")
    print("=" * 64)

    print("\n── Phase 1 : Config ChirpStack via gRPC ──")
    if not get_tenant_from_app(): return
    dp_id = get_or_create_profile()
    if not dp_id: return
    devices = create_devices(dp_id)
    if not devices: return

    print("\n── Phase 2 : Connexion MQTT Passerelle ──")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="lorawan_sim_grpc")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_message = on_verification_msg
    try: client.connect(BROKER_IP, BROKER_PORT, 60)
    except Exception as e:
        print(f"  ❌ MQTT impossible : {e}"); return
    client.loop_start()
    client.subscribe(f"application/{APPLICATION_ID}/device/+/event/up")
    
    gw_topic = f"eu868/gateway/{GATEWAY_ID}/event/up"
    print("\n── Phase 3 : Tir de barrage (Bombardement) ──")
    compteur = 0
    debut = time.time()
    try:
        while True:
            dev = random.choice(devices)
            temp = round(dev["temp_base"] + random.uniform(-1.5, 1.5), 1)
            hum  = round(dev["hum_base"]  + random.uniform(-3.0, 3.0), 1)
            co2  = random.randint(400, 1200)

            payload = encode_sensor_payload(temp, hum, co2)
            phy = build_phy_payload(dev["dev_addr"], dev["nwk_s_key"], dev["app_s_key"], dev["fcnt"], FPORT, payload)
            dev["fcnt"] += 1

            frame = build_uplink_frame_protobuf(phy, -80, 8.5)
            client.publish(gw_topic, frame, qos=0)
            compteur += 1

            if compteur % 5 == 0:
                elapsed = time.time() - debut
                rate = compteur / elapsed if elapsed > 0 else 0
                print(f"  [{datetime.datetime.now().strftime('%H:%M:%S')}] {compteur} trames envoyées ({rate:.1f}/s) | Reçu ChirpStack: {trames_recues} | {dev['name']} T={temp}°C")
            time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        print(f"\n🛑 ARRET SIMULATION. Total envoyé : {compteur}.")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
