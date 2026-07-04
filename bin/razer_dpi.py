#!/usr/bin/env python3

import argparse
import sys

import openrazer.client


def set_dpi(dpi_value):
    """Return True if the DPI was set on at least one mouse, False otherwise."""
    try:
        device_manager = openrazer.client.DeviceManager()
    except openrazer.client.RazerNotFoundError:
        print("Erreur : Aucun périphérique Razer compatible n'a été trouvé.")
        return False

    mice = device_manager.devices
    if not mice:
        print("Erreur : Aucune souris Razer compatible n'a été trouvée.")
        return False

    success = False
    for mouse in mice:
        try:
            print(f"{mouse.name} {dpi_value} DPI")
            mouse.dpi = (dpi_value, dpi_value)
            success = True
        except Exception as e:
            print(
                f"Erreur lors de la définition de la résolution DPI de la souris {mouse.name} : {e}"
            )

    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Définit la résolution (DPI) d'une souris Razer."
    )
    parser.add_argument("dpi", type=int, help="Valeur DPI à définir (nombre entier)")
    args = parser.parse_args()

    sys.exit(0 if set_dpi(args.dpi) else 1)
