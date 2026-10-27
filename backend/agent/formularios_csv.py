import csv
import io

_INICIOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def neutralizar_formula(texto: str) -> str:
    """Excel interpreta como fórmula lo que empieza con = + - @; una comilla simple lo vuelve texto."""
    return "'" + texto if texto[:1] in _INICIOS_DE_FORMULA else texto


def valor_legible(campo: dict, valor) -> str:
    if valor is None:
        return ""
    if campo["tipo"] == "si_no":
        return "Sí" if valor else "No"
    if campo["tipo"] == "fecha":
        partes = str(valor).split("-")
        return f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else str(valor)
    return str(valor)


def a_csv(campos: list[dict], respuestas: list[dict]) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\r\n")
    escritor.writerow(["Fecha"] + [neutralizar_formula(c["etiqueta"]) for c in campos])
    for respuesta in respuestas:
        fila = [str(respuesta["creado_en"])]
        for campo in campos:
            texto = valor_legible(campo, respuesta["valores"].get(campo["clave"]))
            fila.append(texto if campo["tipo"] == "numero" else neutralizar_formula(texto))
        escritor.writerow(fila)
    return salida.getvalue()
