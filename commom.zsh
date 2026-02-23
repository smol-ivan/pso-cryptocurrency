#! /bin/zsh

if (( $+commands[python3] )); then
    export PYTHON="python3"
elif (( $+commands[python] )); then
    export PYTHON="python"
else
    print "Error: ¡Instala python! No se encontró en el PATH."
    exit 1
fi

export VENV_DIR=".venv"
export REQ_FILE="requirements.txt"
