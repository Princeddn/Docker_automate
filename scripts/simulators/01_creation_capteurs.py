"""
================================================================
  1. CRÉATION DES CAPTEURS LORAWAN VIA API gRPC
================================================================
  À ne lancer qu'une seule fois pour préparer ChirpStack.
  Gère proprement l'existence préalable des équipements.
"""

import os
from dotenv import load_dotenv
load_dotenv()

import hashlib
import grpc
from chirpstack_api import api, common

# ================================================================
# CONFIGURATION
# ================================================================
GRPC_SERVER     = "192.168.3.100:8081"
API_KEY = os.getenv("CHIRPSTACK_API_KEY")
APPLICATION_ID  = "YOUR_APPLICATION_ID"
NB_CAPTEURS     = 100

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

def get_grpc_channel(): return grpc.insecure_channel(GRPC_SERVER)
def get_auth_token(): return [("authorization", f"Bearer {API_KEY}")]

def get_tenant_from_app():
    client = api.ApplicationServiceStub(get_grpc_channel())
    try:
        resp = client.Get(api.GetApplicationRequest(id=APPLICATION_ID), metadata=get_auth_token())
        print(f"✅ Application trouvée. Tenant ID = {resp.application.tenant_id}")
        return resp.application.tenant_id
    except grpc.RpcError as e:
        print(f"❌ Erreur lecture Application: {e.details()}")
        return None

def setup_profile(tenant_id):
    client = api.DeviceProfileServiceStub(get_grpc_channel())
    token = get_auth_token()
    
    resp = client.List(api.ListDeviceProfilesRequest(tenant_id=tenant_id, limit=50), metadata=token)
    for p in resp.result:
        if p.name == "Simulated-ABP":
            print(f"ℹ️ Le Profile 'Simulated-ABP' existe déjà.")
            return p.id
            
    req = api.CreateDeviceProfileRequest()
    req.device_profile.tenant_id = tenant_id
    req.device_profile.name = "Simulated-ABP"
    req.device_profile.region = common.Region.EU868
    req.device_profile.mac_version = common.MacVersion.LORAWAN_1_0_3
    req.device_profile.reg_params_revision = common.RegParamsRevision.RP002_1_0_3
    req.device_profile.supports_otaa = False
    req.device_profile.payload_codec_runtime = api.CodecRuntime.JS
    req.device_profile.payload_codec_script = CODEC_JS
    
    resp = client.Create(req, metadata=token)
    print(f"✅ Nouveau Profile 'Simulated-ABP' créé.")
    return resp.id

def list_existing_devices():
    client = api.DeviceServiceStub(get_grpc_channel())
    resp = client.List(api.ListDevicesRequest(application_id=APPLICATION_ID, limit=2500), metadata=get_auth_token())
    return [dev.dev_eui for dev in resp.result]

def create_or_update_devices(dp_id):
    client = api.DeviceServiceStub(get_grpc_channel())
    token = get_auth_token()
    
    print("🔍 Vérification des équipements existants...")
    existing = list_existing_devices()

    for i in range(1, NB_CAPTEURS + 1):
        dev_eui = f"aa00000000{i:06x}"
        dev_addr = 0x01FF0000 + i
        name = f"Sim-Capteur-{i:04d}"
        seed = hashlib.sha256(dev_eui.encode()).digest()
        nwk_s_key = seed[:16]
        app_s_key = seed[16:32]
        
        if dev_eui in existing:
            print(f"  ⚡ {name} existe déjà, réactivation des clés ABP...")
        else:
            req = api.CreateDeviceRequest()
            req.device.dev_eui = dev_eui
            req.device.name = name
            req.device.application_id = APPLICATION_ID
            req.device.device_profile_id = dp_id
            req.device.is_disabled = False
            req.device.skip_fcnt_check = True
            client.Create(req, metadata=token)
            print(f"  ➕ {name} créé.")

        # Activation ABP (écrase la précédente pour remettre les compteurs à 0)
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

def main():
    print("=" * 60)
    print("  INITIALISATION CHIRPSTACK - CREATION CAPTEURS SIMULES")
    print("=" * 60)
    tenant_id = get_tenant_from_app()
    if not tenant_id: return
    dp_id = setup_profile(tenant_id)
    create_or_update_devices(dp_id)
    print("\n🎉 PHASE 1 TERMINEE ! Vous pouvez maintenant lancer le simulateur_radio.py")

if __name__ == "__main__":
    main()
