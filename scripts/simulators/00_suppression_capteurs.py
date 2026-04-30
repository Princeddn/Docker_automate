"""
================================================================
  0. SUPPRESSION DES CAPTEURS SIMULÉS VIA API gRPC
================================================================
  Supprime tous les capteurs "Sim-Capteur-XXXX" de l'application
  ChirpStack, ainsi que le Device Profile "Simulated-ABP".
"""

import os
from dotenv import load_dotenv
load_dotenv()

import grpc
from chirpstack_api import api

# ================================================================
# CONFIGURATION (identique à 01_creation_capteurs.py)
# ================================================================
GRPC_SERVER     = "192.168.3.100:8081"
API_KEY = os.getenv("CHIRPSTACK_API_KEY")
APPLICATION_ID  = os.getenv("APPLICATION_ID")

def get_grpc_channel(): return grpc.insecure_channel(GRPC_SERVER)
def get_auth_token(): return [("authorization", f"Bearer {API_KEY}")]

def delete_all_sim_devices():
    """Supprime tous les devices de l'application qui commencent par 'Sim-Capteur'"""
    client = api.DeviceServiceStub(get_grpc_channel())
    token = get_auth_token()

    # Lister tous les devices de l'application
    resp = client.List(
        api.ListDevicesRequest(application_id=APPLICATION_ID, limit=500),
        metadata=token
    )

    sim_devices = [dev for dev in resp.result if dev.name.startswith("Sim-Capteur")]

    if not sim_devices:
        print("[INFO]  Aucun capteur simulé trouvé dans l'application.")
        return 0

    print(f"[SEARCH] {len(sim_devices)} capteur(s) simulé(s) trouvé(s).\n")

    deleted = 0
    for dev in sim_devices:
        try:
            client.Delete(
                api.DeleteDeviceRequest(dev_eui=dev.dev_eui),
                metadata=token
            )
            print(f"  [DELETE]  {dev.name} ({dev.dev_eui}) supprimé.")
            deleted += 1
        except grpc.RpcError as e:
            print(f"  [ERREUR] Erreur suppression {dev.name}: {e.details()}")

    return deleted

def delete_sim_profile():
    """Supprime le Device Profile 'Simulated-ABP' s'il existe"""
    # On a besoin du tenant_id
    app_client = api.ApplicationServiceStub(get_grpc_channel())
    token = get_auth_token()

    try:
        resp = app_client.Get(
            api.GetApplicationRequest(id=APPLICATION_ID),
            metadata=token
        )
        tenant_id = resp.application.tenant_id
    except grpc.RpcError as e:
        print(f"[ERREUR] Impossible de lire l'application: {e.details()}")
        return

    dp_client = api.DeviceProfileServiceStub(get_grpc_channel())
    resp = dp_client.List(
        api.ListDeviceProfilesRequest(tenant_id=tenant_id, limit=50),
        metadata=token
    )

    for p in resp.result:
        if p.name == "Simulated-ABP":
            try:
                dp_client.Delete(
                    api.DeleteDeviceProfileRequest(id=p.id),
                    metadata=token
                )
                print(f"\n[DELETE]  Device Profile 'Simulated-ABP' supprimé.")
            except grpc.RpcError as e:
                print(f"\n[ERREUR] Erreur suppression du Profile: {e.details()}")
            return

    print("\n[INFO]  Aucun Device Profile 'Simulated-ABP' trouvé.")

def main():
    print("=" * 60)
    print("  [CLEAN]  NETTOYAGE CHIRPSTACK - SUPPRESSION CAPTEURS SIMULÉS")
    print("=" * 60)

    # 1. Supprimer les devices
    deleted = delete_all_sim_devices()

    # 2. Supprimer le Device Profile (seulement si tous les devices sont supprimés)
    if deleted > 0:
        delete_sim_profile()

    print(f"\n[OK] Nettoyage terminé ! ({deleted} capteur(s) supprimé(s))")

if __name__ == "__main__":
    main()
