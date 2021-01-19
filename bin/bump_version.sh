#!/usr/bin/env sh
if [ -z "$1" ]; then
    echo "Must supply a new version number."
    exit 1
fi
sed -i "s/version = '.*'/version = '$1'/" setup.py
sed -i "s:<property name=\"version\">0.3.0</property>:<property name=\"version\">$1</property>:" plots/ui/about.glade
dch --newversion $1 --distribution focal --maintmaint v$1
sed -i res/com.github.alexhuntley.Plots.metainfo.xml -f - <<EOF
s|<releases>|<releases>\n\
    <release version="$1" date="$(date +%F)">\n\
      <description>\n\
        <p>$2</p>\n\
      </description>\n\
    </release>|
EOF
git add setup.py plots/ui/about.glade debian/changelog res/com.github.alexhuntley.Plots.metainfo.xml
git commit -m "release v$1"
git tag -am "Plots $1" "v$1"
