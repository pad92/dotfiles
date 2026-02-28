#!/bin/sh

OUTPUT=""
capacity=""

# On vérifie si le répertoire existe pour éviter l'erreur
if [ ! -d /sys/class/power_supply ]; then
    exit 0
fi

# On boucle sur chaque dossier trouvé dans power_supply
for ps in /sys/class/power_supply/*; do
    # On vérifie que c'est bien un répertoire (évite les erreurs si le dossier est vide)
    [ ! -d "$ps" ] && continue

    type=$(cat "$ps/type")

    # Cas du Secteur
    if [ "$type" = "Mains" ]; then
        if [ -f "$ps/online" ] && [ "$(cat "$ps/online")" = "1" ]; then
            OUTPUT=" "
        fi
    fi

    # Cas de la Batterie
    if [ "$type" = "Battery" ]; then
        if [ -f "$ps/capacity" ]; then
            cap=$(cat "$ps/capacity")
            capacity="${cap}%"

            if [ "$cap" -gt 90 ]; then icon=" "
            elif [ "$cap" -gt 60 ]; then icon=" "
            elif [ "$cap" -gt 40 ]; then icon=" "
            elif [ "$cap" -gt 10 ]; then icon=" "
            else icon=" "; fi

            # On ajoute l'icône à l'output existant (qui peut contenir la prise )
            OUTPUT="${OUTPUT}${icon}"
        fi
    fi
done

# Si rien n'est trouvé (PC fixe sans batterie), on sort sans rien écrire
if [ -z "$OUTPUT" ] && [ -z "$capacity" ]; then
    exit 0
fi

echo "${OUTPUT} ${capacity}"
