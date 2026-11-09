#!/bin/sh
# Шрифты writer для office. Api кладёт скачанный шрифт в папку custom-fonts (FONTS_DIR
# на хосте), а этот сторож замечает новые файлы и пересобирает список шрифтов office.
# Пересборка перезапускает службы office, открытые тексты переподключаются сами. Ждём,
# пока папка 10 с не меняется: семейство приходит несколькими файлами, а пересобирать
# хватит один раз. Запускает сторожа compose рядом со штатным запуском office
fonts=/var/www/onlyoffice/Data/custom-fonts
seen=$(ls -lR "$fonts" 2>/dev/null)
last=$seen
while sleep 10; do
  now=$(ls -lR "$fonts" 2>/dev/null)
  if [ "$now" != "$seen" ] && [ "$now" = "$last" ]; then
    seen=$now
    documentserver-generate-allfonts.sh
  fi
  last=$now
done
