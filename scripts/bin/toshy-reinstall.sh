#!/usr/bin/bash


# Launch the bootstrap reinstaller script

echo        # blank line to separate from command

echo "This usually works but could potentially break a working Toshy install."
echo "Not advised if you don't have some time to revert to a working release."
echo
read -r -p "Are you sure you want to reinstall Toshy from a GitHub branch? [y/N]: " result


if [ "$result" == "y" ] || [ "$result" == "Y" ]; then
    :   # no-op lets script continue
else
    echo
    echo "Toshy reinstall canceled."
    echo
    exit 0
fi


if [ -f "$HOME/.config/toshy/scripts/bootstrap.sh" ]; then
    exec "$HOME/.config/toshy/scripts/bootstrap.sh"
else
    echo "Bootstrap script missing. Exiting."
    echo 
    exit 1
fi
