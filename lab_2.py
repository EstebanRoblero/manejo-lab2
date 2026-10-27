import os 
import json 
import hashlib
import datetime
import zipfile
import tkinter as tk
from tkinter import messagebox


try:
    from tkinter import PDF
except ImportError:
    PDF = None

# Configuración
#=======================================================
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

#FUNCIONES DEL FORMATO DE REGISTRO EN BYTES
#==============================================


def ajustar_campo(texto, longitud):
    datos= str(texto).strip().encode("utf-8")[:longitud]
    datos = datos.decode("utf-8", errors = "ignore").encode("utf-8")
    return datos.ljust(longitud, b" ")


def codificar_elregistro(valores):
    cuerpo= b"".join(ajustar_campo(valores[n], l) for n, l in CAMPOS)
    registro = cuerpo + b"\n"
    assert len(registro) == TAMANIO_DELREGISTRO
    return registro


def decodificar_elregistro(raw):
    if len(raw) != TAMANIO_DELREGISTRO or not raw.endswith(b"\n"):
        raise ValueError("el registro no tiene el tamaño o formato correcto")

    valores, pos = {}, 0
    for nombre, largo in CAMPOS:
        valores[nombre]= raw[pos: pos + largo].decode("utf-8").strip()
        pos += largo
    return valores

# el fpdf2 con fuentes base que solo admite latin-1
#============================
def sanear_latin1(texto):
    return str(texto).encode("latin-1", "replace").decode("latin-1")

#aplicaiones 

class AgendaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Agenda de contactos de Aceso aletorio ")
        self.indice = {}
        self.entries= {}
        self.crear_menu()
        self.cargar_indice()
        self.cargar_interfaz()

        #ventana de la interfaz visible
        self.root.after(200, lambda: self.veridicar_integridad(manual=False))


    #indice

    def cargar_indice(self):
        self.indice ={}
        if os.path.exists(ARCHIVO_INDICE):
            try:
                with open(ARCHIVO_INDICE, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                if not isinstance(datos, dict):
                    raise ValueError("El indice de este no es un diccionario ")
                total= self.total_registros()
                for k, v in datos.items():
                    if not isinstance(k, str) or not isinstance(v, int) or not 0<= v < total:
                        raise ValueError("El indice contiene los datos invalidos")
                self.indice = datos
                return
            except (OSError, ValueError) as e:
                messagebox.showerror("Error", f"el indice esta dañado no se puede usar el {os.path.basename(ARCHIVO_INDICE)}:\n{e}\n\n")

        if os.path.exists(ARCHIVO_DATOS):
            self.reconstruir_elindice(silencioso=True)

    def guardar_elindice(self):
        """Escritura segura de archivo temporal + reemplazo."""
        tmp = ARCHIVO_INDICE + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.indice, f, indent=2)
            os.replace(tmp, ARCHIVO_INDICE)
            return True
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo guardar el índice:\n{e}")
            return False

    def reconstruir_elindice(self, silencioso=False):
        if not os.path.exists(ARCHIVO_DATOS):
            if not silencioso:
                messagebox.showerror("Error", "El archivo de contactos no existe")
            return
        nuevo = {}
        try:
            with open(ARCHIVO_DATOS, "rb") as f:
                num = 0
                while True:
                    raw = f.read(TAMANIO_DELREGISTRO)
                    if not raw:
                        break
                    valores = decodificar_elregistro(raw)
                    nuevo[str(int(valores["id"]))] = num
                    num += 1
        except (OSError, ValueError) as e:
            messagebox.showerror("Error", f"No se pudo reconstruir el indice:\n{e}")
            return
        self.indice = nuevo
        if self.guardar_elindice() and not silencioso:
            messagebox.showinfo("indice", f"el indice reconstruido con {len(nuevo)} contactos.")
        elif silencioso:
            messagebox.showinfo("indice", f"el indice reconstruido con {len(nuevo)} contactos.")
            
    def total_registros(self):
        try:
            return os.path.getsize(ARCHIVO_DATOS) // TAMANIO_DELREGISTRO
        except OSError:
            return 0