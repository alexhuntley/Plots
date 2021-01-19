#!/usr/bin/env sh
if [ -z "$1" ]; then
    echo "Must supply a new version number."
    exit 1
fi
sed -i "s/version = '.*'/version = '$1'/" setup.py
sed -i "s:<property name=\"version\">0.3.0</property>:<property name=\"version\">$1</property>:" plots/ui/about.glade
dch --newversion $1 --distribution focal --maintmaint v$1
