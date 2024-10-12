#!/usr/bin/env python3

import argparse
import openrazer.client

def set_dpi(dpi_value):
  try:
    device_manager = openrazer.client.DeviceManager()
  except openrazer.client.RazerNotFoundError:
    print("Erreur : Aucun périphérique Razer compatible n'a été trouvé.")
    return

  mice = device_manager.devices
  if not mice:
    print("Erreur : Aucune souris Razer compatible n'a été trouvée.")
    return

  for mouse in mice:
    try:
      # Assurez-vous que dpi_value est un tuple de deux entiers
      if isinstance(dpi_value, int):
        print(f"{mouse.name} {dpi_value} DPI")
        dpi_value = (dpi_value, dpi_value)
        mouse.dpi = dpi_value
    except Exception as e:  # Capture toutes les exceptions
      print(f"Erreur lors de la définition de la résolution DPI de la souris {mouse.name} : {e}")

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Définit la résolution (DPI) d'une souris Razer.")
  parser.add_argument("dpi", type=int, help="Valeur DPI à définir (nombre entier)")
  args = parser.parse_args()

  set_dpi(args.dpi)
