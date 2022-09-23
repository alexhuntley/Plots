#!/bin/sh
find plots -iname "*.py" | xargs xgettext --from-code=UTF-8 --output=plots-python.pot
find plots/ui -iname "*.ui" | xargs xgettext --from-code=UTF-8 --output=plots-ui.pot --language=Glade
msgcat --use-first plots-python.pot plots-ui.pot > plots/locale/plots.pot
rm plots-python.pot plots-ui.pot
