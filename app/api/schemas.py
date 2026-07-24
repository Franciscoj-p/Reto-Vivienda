from pydantic import BaseModel, ConfigDict, Field


class LeadInput(BaseModel):
    """Esquema flexible del lead; los campos extra se conservan en la respuesta."""

    model_config = ConfigDict(extra="allow")

    nombre: str | None = None
    afiliado: bool = False
    categoria: str | None = None
    antiguedad_meses: int | None = None
    ingresos_mensuales: float = Field(default=0, ge=0)
    edad: int | None = None
    personas_a_cargo: int | None = None
    cabeza_de_hogar: bool = False
    tiene_discapacidad_hogar: bool = False
    propietario_vivienda: bool = False
    tipo_empresa: str | None = None
    cesantias: float = Field(default=0, ge=0)
    ahorros: float = Field(default=0, ge=0)
    zona_preferida: str | None = None
    origen: str | None = None
    tipo_cotizante: str | None = None                    # "dependiente" | "independiente" | "pensionado"
    subsidio_vivienda_previo: bool = False
    subsidio_previo_fue_arrendamiento: bool = False
    valor_vivienda_deseada: float | None = None           # COP, opcional
