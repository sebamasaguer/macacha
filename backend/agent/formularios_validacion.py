import math
import re
import unicodedata
from datetime import date

from agent.admin.email_contacto import normalizar_email_contacto

TIPOS = ("texto", "texto_largo", "dni", "telefono", "email", "numero", "fecha", "si_no", "opcion")
MAX_CAMPOS = 30
MAX_OPCIONES = 20
MAX_OPCION = 80
MAX_ETIQUETA = 120
MAX_TEXTO = 200
MAX_TEXTO_LARGO = 1000

_SI = {"si", "sí", "s", "true", "verdadero"}
_NO = {"no", "n", "false", "falso"}


class ErrorDeCampo(ValueError):
    """El valor no cumple las reglas de su tipo; el mensaje se le puede mostrar a la persona."""


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def generar_clave(etiqueta: str, existentes: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", _sin_acentos(etiqueta).lower()).strip("_")[:40] or "campo"
    clave, n = base, 2
    while clave in existentes:
        clave = f"{base}_{n}"
        n += 1
    return clave


def _normalizar_texto(valor, maximo: int, una_linea: bool) -> str:
    texto = " ".join(str(valor).split()) if una_linea else str(valor).strip()
    if len(texto) > maximo:
        raise ErrorDeCampo(f"Es demasiado largo (máximo {maximo} caracteres).")
    return texto


def _normalizar_dni(valor) -> str:
    digitos = re.sub(r"[.\s]", "", str(valor))
    if not re.fullmatch(r"\d{7,8}", digitos):
        raise ErrorDeCampo("El DNI debe tener 7 u 8 números.")
    return digitos


def _normalizar_telefono(valor) -> str:
    limpio = str(valor).strip()
    if not re.fullmatch(r"\+?[\d\s\-()]+", limpio):
        raise ErrorDeCampo("El teléfono solo puede tener números, espacios, guiones y paréntesis.")
    digitos = re.sub(r"\D", "", limpio)
    if not 8 <= len(digitos) <= 15:
        raise ErrorDeCampo("El teléfono debe tener entre 8 y 15 números.")
    return ("+" if limpio.startswith("+") else "") + digitos


def _normalizar_email(valor) -> str:
    try:
        email = normalizar_email_contacto(str(valor))
    except ValueError as error:
        raise ErrorDeCampo(str(error)) from None
    if email is None:
        raise ErrorDeCampo("Ingresá un email.")
    return email


def _normalizar_numero(valor):
    if isinstance(valor, bool):
        raise ErrorDeCampo("Ingresá un número.")
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        try:
            numero = float(str(valor).strip().replace(",", "."))
        except ValueError:
            raise ErrorDeCampo("Ingresá un número.") from None
    if math.isnan(numero) or math.isinf(numero):
        raise ErrorDeCampo("Ingresá un número.")
    return int(numero) if numero == int(numero) else numero


def _normalizar_fecha(valor) -> str:
    texto = str(valor).strip()
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if iso:
        anio, mes, dia = (int(x) for x in iso.groups())
    else:
        local = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
        if not local:
            raise ErrorDeCampo("Ingresá la fecha como día/mes/año, por ejemplo 25/12/1990.")
        dia, mes, anio = (int(x) for x in local.groups())
    try:
        return date(anio, mes, dia).isoformat()
    except ValueError:
        raise ErrorDeCampo("Esa fecha no existe.") from None


def _normalizar_si_no(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    texto = str(valor).strip().lower()
    if texto in _SI:
        return True
    if texto in _NO:
        return False
    raise ErrorDeCampo("Respondé sí o no.")


def _normalizar_opcion(valor, opciones) -> str:
    texto = str(valor).strip().lower()
    for opcion in opciones or []:
        if opcion.strip().lower() == texto:
            return opcion
    raise ErrorDeCampo("Elegí una de estas opciones: " + ", ".join(opciones or []) + ".")


def normalizar_valor(campo: dict, valor):
    tipo = campo["tipo"]
    if tipo == "texto":
        return _normalizar_texto(valor, MAX_TEXTO, una_linea=True)
    if tipo == "texto_largo":
        return _normalizar_texto(valor, MAX_TEXTO_LARGO, una_linea=False)
    if tipo == "dni":
        return _normalizar_dni(valor)
    if tipo == "telefono":
        return _normalizar_telefono(valor)
    if tipo == "email":
        return _normalizar_email(valor)
    if tipo == "numero":
        return _normalizar_numero(valor)
    if tipo == "fecha":
        return _normalizar_fecha(valor)
    if tipo == "si_no":
        return _normalizar_si_no(valor)
    if tipo == "opcion":
        return _normalizar_opcion(valor, campo.get("opciones"))
    raise ValueError(f"Tipo de campo desconocido: {tipo}")


def validar_valores(campos: list[dict], valores: dict) -> tuple[dict, dict]:
    normalizados: dict = {}
    errores: dict = {}
    for campo in campos:
        clave = campo["clave"]
        crudo = valores.get(clave) if isinstance(valores, dict) else None
        vacio = crudo is None or (isinstance(crudo, str) and not crudo.strip())
        if vacio:
            if campo["obligatorio"]:
                errores[clave] = "Este dato es obligatorio."
            continue
        try:
            normalizados[clave] = normalizar_valor(campo, crudo)
        except ErrorDeCampo as error:
            errores[clave] = str(error)
    return normalizados, errores


def validar_definicion(campos: list[dict]) -> None:
    if not campos:
        raise ValueError("El formulario necesita al menos un campo.")
    if len(campos) > MAX_CAMPOS:
        raise ValueError(f"Un formulario admite hasta {MAX_CAMPOS} campos.")
    if sum(1 for c in campos if c["tipo"] == "dni") > 1:
        raise ValueError("Un formulario admite un solo campo DNI.")
    for campo in campos:
        if campo["tipo"] not in TIPOS:
            raise ValueError(f"Tipo de campo desconocido: {campo['tipo']}.")
        etiqueta = (campo.get("etiqueta") or "").strip()
        if not etiqueta or len(etiqueta) > MAX_ETIQUETA:
            raise ValueError(f"Cada campo necesita una etiqueta de hasta {MAX_ETIQUETA} caracteres.")
        if campo["tipo"] == "opcion":
            opciones = [o.strip() for o in (campo.get("opciones") or [])]
            repetidas = len({o.lower() for o in opciones}) != len(opciones)
            if not 2 <= len(opciones) <= MAX_OPCIONES or repetidas or any(not o or len(o) > MAX_OPCION for o in opciones):
                raise ValueError(
                    f"La lista «{etiqueta}» necesita entre 2 y {MAX_OPCIONES} opciones distintas, de hasta {MAX_OPCION} caracteres."
                )
