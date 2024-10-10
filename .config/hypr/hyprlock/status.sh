#!/bin/bash

# Vérifier si le répertoire /sys/class/power_supply existe
if [ ! -d /sys/class/power_supply ]; then
  exit 0
fi

# Parcourir toutes les sources d'alimentation
for power_supply in /sys/class/power_supply/*; do
  # Extraire le nom de la source
  power_supply_name=$(basename "$power_supply")

  # Vérifier si la source est de type "Mains"
  if grep -q "Mains" "$power_supply/type"; then
    # Vérifier l'état du secteur en utilisant le fichier "online"
    if [ -f "$power_supply/online" ]; then
      status=$(cat "$power_supply/online")
      if [ "$status" = "1" ]; then
        OUTPUT="${OUTPUT}  "
      fi
    fi
  fi

  # Vérifier si la source est de type "Battery"
  if grep -q "Battery" "$power_supply/type"; then
    # Vérifier si le fichier "capacity" existe pour la batterie
    if [ -f "$power_supply/capacity" ]; then
      capacity=$(cat "$power_supply/capacity")
      OUTPUT="${OUTPUT} "
    fi
  fi

done

echo "${OUTPUT}  ${capacity}%"
