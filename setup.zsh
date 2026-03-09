#! /bin/zsh

source "commom.zsh"

if [[ ! -d $VENV_DIR ]]; then
    print "No existe entorno virtual de python"
    print "Creando entorno ..."

    $PYTHON -m venv $VENV_DIR

    source "$VENV_DIR/bin/activate"

    pip install --upgrade pip

fi

print "Cargando entorno virtual..."

source "$VENV_DIR/bin/activate"

if [[ ! -f $REQ_FILE ]]; then
    print "Hubo un problema, no existe archivo de requerimientos"
    exit 1
fi

print "Instalando requerimientos..."

pip install -r $REQ_FILE


