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

ARCHIVO_JSON = ruta("archivo.json")
ARCHIVO_ZIP = ruta("respaldo.zip")
ARCHIVO_PDF = ruta("reportede_contactos.pdf")
ARCHIVO_HASH = ruta("contactos.sha256")
ARCHIVO_INDICE = ruta("indice.json")
ARCHIVO_DATOS = ruta("contactos.dat")


CAMPOS = [("id", 8), ("nombre", 30), ("telefono", 15), ("correo", 26), ("ciudad", 20)]

ETIQUETAS = {"id": "ID", "nombre": "Nombre", "telefono": "Teléfono","correo": "Correo", "ciudad": "Ciudad"}

LEN_DATOS = sum(largo for _, largo in CAMPOS)

TAMANIO_DELREGISTRO = LEN_DATOS + 1
assert TAMANIO_DELREGISTRO == 100

#FUNCIONES DEL FORMATO DE REGISTRO EN BYTES
#==============================================


def ajustar_campo(texto, longitud):
    datos = str(texto).strip().encode("utf-8")[:longitud]
    datos = datos.decode("utf-8", errors="ignore").encode("utf-8")
    return datos.ljust(longitud, b" ")


def codificar_elregistro(valores):
    cuerpo = b"".join(ajustar_campo(valores[n], l) for n, l in CAMPOS)
    registro = cuerpo + b"\n"
    assert len(registro) == TAMANIO_DELREGISTRO
    return registro


def decodificar_elregistro(raw):
    if len(raw) != TAMANIO_DELREGISTRO or not raw.endswith(b"\n"):
        raise ValueError("el registro no tiene el tamaño o formato correcto")

    valores, pos = {}, 0
    for nombre, largo in CAMPOS:
        valores[nombre] = raw[pos: pos + largo].decode("utf-8").strip()
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
        self.entries = {}
        self.crear_menu()
        self.cargar_indice()
        self.cargar_interfaz()

        #ventana de la interfaz visible
        self.root.after(200, lambda: self.verificar_integridad(manual=False))


    #indice

    def cargar_indice(self):
        self.indice = {}
        if os.path.exists(ARCHIVO_INDICE):
            try:
                with open(ARCHIVO_INDICE, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                if not isinstance(datos, dict):
                    raise ValueError("El indice de este no es un diccionario ")
                total = self.total_registros()
                for k, v in datos.items():
                    if not isinstance(k, str) or not isinstance(v, int) or not 0 <= v < total:
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

    #hash

    @staticmethod
    def calcular_hash():
        hasher = hashlib.sha256()
        with open(ARCHIVO_DATOS, "rb") as f:
            for bloque in iter(lambda: f.read(65536), b""):
                hasher.update(bloque)
        return hasher.hexdigest()

    def actualizar_hash(self):
        if not os.path.exists(ARCHIVO_DATOS):
            return
        try:
            with open(ARCHIVO_HASH, "w", encoding="utf-8") as f:
                f.write(self.calcular_hash())
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo guardar el hash:\n{e}")

    def verificar_integridad(self, manual=True):
        """Compara el hash actual contra el guardado (al iniciar o desde Herramientas)."""
        if not os.path.exists(ARCHIVO_DATOS):
            if manual:
                messagebox.showinfo("Integridad", "Todavía no existe el archivo de contactos.")
            return
        try:
            actual = self.calcular_hash()
            if not os.path.exists(ARCHIVO_HASH):
                self.actualizar_hash()
                if manual:
                    messagebox.showinfo("Integridad", "No había hash guardado; se generó uno nuevo.")
                return
            with open(ARCHIVO_HASH, "r", encoding="utf-8") as f:
                guardado = f.read().strip()
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo verificar la integridad:\n{e}")
            return

        if actual != guardado:
            messagebox.showwarning(
                "Alerta de Integridad",
                "El archivo de contactos fue modificado fuera de la aplicación.\n\n"
                f"Hash guardado:\n{guardado}\n\nHash actual:\n{actual}")
            if messagebox.askyesno("Integridad", "¿Aceptar el estado actual y recalcular el hash?"):
                self.actualizar_hash()
                self.reconstruir_elindice(silencioso=True)
        elif manual:
            messagebox.showinfo("Integridad", "El archivo está íntegro (el hash coincide).")

#interfaz grafica
    def cargar_interfaz(self):
        form = tk.Frame(self.root)
        form.pack(padx=10, pady=5)

        for i, (nombre, largo) in enumerate(CAMPOS):
            tk.Label(form, text=f"{ETIQUETAS[nombre]}:").grid(row=i, column=0, sticky="e", padx=5, pady=2)
            entry = tk.Entry(form, width=30)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.entries[nombre] = entry

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Agregar", command=self.agregar_contacto).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Buscar ID", command=self.buscar_contacto).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Modificar", command=self.modificar_contacto).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Limpiar", command=self.limpiar_formulario).pack(side="left", padx=3)

    def crear_menu(self):
        barra = tk.Menu(self.root)

        m_contactos = tk.Menu(barra, tearoff=0)
        m_contactos.add_command(label="Agregar contacto", command=self.agregar_contacto)
        m_contactos.add_command(label="Buscar por ID", command=self.buscar_contacto)
        m_contactos.add_command(label="Modificar contacto", command=self.modificar_contacto)
        barra.add_cascade(label="Contactos", menu=m_contactos)

        m_exportar = tk.Menu(barra, tearoff=0)
        m_exportar.add_command(label="Exportar a JSON", command=self.exportar_json)
        m_exportar.add_command(label="Generar reporte PDF", command=self.generar_pdf)
        barra.add_cascade(label="Exportar", menu=m_exportar)

        m_herr = tk.Menu(barra, tearoff=0)
        m_herr.add_command(label="Verificar integridad", command=self.verificar_integridad)
        m_herr.add_command(label="Crear respaldo ZIP", command=self.crear_respaldo)
        m_herr.add_command(label="Información del archivo", command=self.mostrar_info_archivo)
        barra.add_cascade(label="Herramientas", menu=m_herr)

        m_ayuda = tk.Menu(barra, tearoff=0)
        m_ayuda.add_command(label="Ayuda", command=lambda: messagebox.showinfo("Ayuda", "Sistemas de contactos."))
        m_ayuda.add_command(label="Acerca de", command=lambda: messagebox.showinfo("Acerca de", "Laboratorio No. 2"))
        barra.add_cascade(label="Ayuda", menu=m_ayuda)

        self.root.config(menu=barra)

    def leer_formulario(self):
        return {n: self.entries[n].get().strip() for n, _ in CAMPOS}

    def llenar_formulario(self, valores):
        for n, _ in CAMPOS:
            self.entries[n].delete(0, "end")
            self.entries[n].insert(0, valores.get(n, ""))

    def limpiar_formulario(self):
        self.llenar_formulario({})

#CRUD con acceso aleatorio
    def agregar_contacto(self):
        valores = self.leer_formulario()
        id_txt = valores["id"]
        if not id_txt or not id_txt.isdigit():
            messagebox.showwarning("Error", "Ingrese un ID numérico válido.")
            return
        if id_txt in self.indice:
            messagebox.showwarning("Error", f"El ID {id_txt} ya existe.")
            return

        try:
            modo = "r+b" if os.path.exists(ARCHIVO_DATOS) else "w+b"
            with open(ARCHIVO_DATOS, modo) as f:
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                num = pos // TAMANIO_DELREGISTRO
                f.write(codificar_elregistro(valores))

            self.indice[id_txt] = num
            self.guardar_elindice()
            self.actualizar_hash()
            self.limpiar_formulario()
            messagebox.showinfo("Éxito", f"Contacto guardado en registro #{num} (pos: {pos})")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def buscar_contacto(self):
        id_txt = self.entries["id"].get().strip()
        if id_txt not in self.indice:
            messagebox.showinfo("Búsqueda", f"No se encontró el ID {id_txt}")
            return

        num = self.indice[id_txt]
        try:
            with open(ARCHIVO_DATOS, "rb") as f:
                f.seek(num * TAMANIO_DELREGISTRO)
                raw = f.read(TAMANIO_DELREGISTRO)
                valores = decodificar_elregistro(raw)

            self.llenar_formulario(valores)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def modificar_contacto(self):
        valores = self.leer_formulario()
        id_txt = valores["id"]
        if id_txt not in self.indice:
            messagebox.showwarning("Error", f"No existe contacto con ID {id_txt}")
            return

        num = self.indice[id_txt]
        try:
            with open(ARCHIVO_DATOS, "r+b") as f:
                f.seek(num * TAMANIO_DELREGISTRO)
                f.write(codificar_elregistro(valores))

            self.actualizar_hash()
            messagebox.showinfo("Éxito", "Contacto modificado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

