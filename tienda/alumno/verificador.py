"""PARTE 2 — Las dos revisiones que hace un programa antes de que una persona mire nada.

2a. `verificar(sugerencia)`: las reglas del negocio. Se usa en la columna «verificador» de la
    bandeja y en la acción «Aprobar y aplicar» (Parte 3).
2b. `validar_forma(item)`: la puerta de entrada. La usa `python manage.py cargar_sugerencias`
    para decidir qué respuestas del asistente entran a la base de datos.

Comprueba tu avance con: python manage.py duelo
"""

from decimal import Decimal, InvalidOperation  # noqa: F402  (los vas a necesitar)

from tienda.models import Producto, Sugerencia  # noqa: F402

VARIACION_MAXIMA_PRECIO = Decimal("1.30")  # ±30 % sobre el precio actual
STOCK_MAXIMO = 999
CLAVES = {"producto", "campo", "valor", "motivo"}


def verificar(sugerencia):
    problemas = []

    campo = sugerencia.campo
    valor = sugerencia.valor_propuesto

    if campo == "precio":
        precio_actual = sugerencia.producto.precio

        if valor <= 0:
            problemas.append("El precio tiene que ser mayor que 0")

        minimo = precio_actual * Decimal("0.70")
        maximo = precio_actual * VARIACION_MAXIMA_PRECIO

        if valor < minimo or valor > maximo:
            problemas.append("El precio supera la variación de ±30 %")

    elif campo == "stock":
        if valor != valor.to_integral_value():
            problemas.append("El stock debe ser un número entero")

        if valor < 0:
            problemas.append("El stock no puede ser negativo")

        if valor > STOCK_MAXIMO:
            problemas.append("El stock no puede pasar de 999")

    else:
        problemas.append("campo desconocido")

    return problemas


def validar_forma(item):
    # Comprobar las claves obligatorias
    faltantes = CLAVES - item.keys()

    if faltantes:
        raise ValueError(f"le faltan claves: {faltantes}")

    # Buscar el producto
    producto = Producto.objects.filter(nombre__iexact=item["producto"]).first()

    if producto is None:
        raise ValueError(f"{item['producto']} no existe en el catálogo")

    # Validar el campo
    if item["campo"] not in ("precio", "stock"):
        raise ValueError("campo desconocido")

    # Convertir el valor
    try:
        valor = Decimal(str(item["valor"]))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"El valor '{item['valor']}' no es un número")

    return producto, valor
