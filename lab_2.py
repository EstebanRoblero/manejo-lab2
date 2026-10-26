import os 
import json 
import haslib
import detetime
import zipfile
import tkinter as tk
import tkinter import messagebox


try:
    from tkinter import PDF
except ImportError:
    PDF = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def ruta(nombre):
    return os.path.join(BASE_DIR, nombre)


ARCHIVO_JSON = ruta ("archivo.json")
ARCHIVO_ZIP = ruta("respaldo.zip")
ARCHIVO_PDF = ruta("reportede_contactos.pdf")
ARCHIVO_HASH = ruta("contactos.sha256")
ARCHIVO_INDICE = ruta("indice.json")
ARCHIVO_DATOS = ruta("contactos.dat")


CAMPOS = [("id", 8), ("nombre", 30), ("telefono", 15), ("correo", 26), ("ciudad", 20)]

ETIQUETAS = {"id": "ID", "nombre": "Nombre", "telefono": "Teléfono","correo": "Correo", "ciudad": "Ciudad"}

LEN_DATOS =sum(largo for _, largo in CAMPOS)

TAMANIO_DELREGISTRO = LEN_DATOS +1
assert TAMANIO_DELREGISTRO == 100

def ajustar_campo(texto, longitud):
    datos= str(texto).strip().encode("utf-8")[:longitud]
    datos = datos.decode("utf-8", errors = "ignore").encode("utf-8")
    return datos.ljust(longitud, b" ")


def codificar_elregistro(valores):
    cuerpo= b"".join(ajustar_campo(valores[n], l) for n, l in CAMPOS)
    registro = cuerpo + b "\n"
    assert len(registro) == TAMANIO_DELREGISTRO
    return registro
