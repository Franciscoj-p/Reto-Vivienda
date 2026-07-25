from pydantic import BaseModel, ConfigDict, Field


class CondicionesEspeciales(BaseModel):
    """Condiciones que suman en score y pueden intervenir en reglas de negocio."""

    model_config = ConfigDict(extra="allow")

    cabeza_de_hogar: bool = False
    discapacidad_hogar: bool = False
    mayor_65_anos: bool = False


class Finanzas(BaseModel):
    """Datos financieros del hogar usados en cierre financiero y scoring."""

    model_config = ConfigDict(extra="allow")

    cesantias: float = Field(default=0, ge=0)
    ahorros: float = Field(default=0, ge=0)
    credito_preaprobado: bool = False


class LeadInput(BaseModel):
    """Esquema flexible del lead; los campos extra se conservan en la respuesta."""

    model_config = ConfigDict(extra="allow")

    id_usuario: str | None = None
    nombre: str | None = None
    afiliado: bool = False
    categoria: str | None = None
    antiguedad_meses: int | None = None
    tipo_cotizante: str | None = None      # "dependiente" | "independiente" | "pensionado"
    ingresos_mensuales: float = Field(default=0, ge=0)
    grupo_sisben: str | None = None        # ej. "C2"; None/fuera de A1-D21 -> no califica
    edad: int | None = None
    personas_a_cargo: int | None = None
    condiciones_especiales: CondicionesEspeciales = Field(default_factory=CondicionesEspeciales)
    propietario_vivienda: bool = False
    subsidio_previo: bool = False
    subsidio_previo_fue_arrendamiento: bool = False
    finanzas: Finanzas = Field(default_factory=Finanzas)
    tipo_empresa: str | None = None
    zona: str | None = None                # Zona geográfica ("urbana", "rural", etc.)
    zona_preferida: str | None = None
    proyecto_interes: str | None = None    # Proyecto por el que llega el lead
    valor_vivienda_deseada: float | None = None   # COP, opcional
    origen: str | None = None