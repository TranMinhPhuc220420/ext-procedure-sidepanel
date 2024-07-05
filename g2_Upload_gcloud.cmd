@REM SET PROJECT=ext-procedure-side-panel
SET PROJECT=vn-sateraito-apps-fileserver2
SET VERSION=ext2005

TITLE %PROJECT% ver=%VERSION%(gcloud)

cd .\src

call gcloud app deploy app.yaml --project=%PROJECT% --version=%VERSION% --no-cache --no-promote --no-stop-previous-version

cd ..

pause
