# Pruebas automatizadas

Suite de pruebas del sistema: reglas de la base, roles de MySQL, aplicación web y reportes.
Solo usa `unittest` y las dependencias de `requirements.txt`.

## Cómo ejecutarla

Desde la raíz del proyecto, con el entorno virtual activo:

```powershell
python tests/run_tests.py
```

Para correr solo una parte, indicar el prefijo del archivo:

```powershell
python tests/run_tests.py --solo test_05
```

La ejecución completa regenera dos archivos:

- `tests/casos_de_prueba.md`: los casos de prueba, con entrada, resultado esperado, resultado obtenido y estado.
- `tests/resultados.json`: los mismos datos, para reutilizarlos en el informe.

## No toca tu base de datos

Cada ejecución levanta una instancia **temporal** de MySQL en un puerto libre, con datos propios, instala los
cuatro scripts y la elimina al terminar. Nunca se conecta al servidor instalado, que es importante porque
`creacion-tablas.sql` empieza con `DROP DATABASE`.

Solo hace falta tener MySQL 8 instalado, porque se usan sus ejecutables. Si no están en
`C:\Program Files\MySQL\MySQL Server 8.x\bin`, indicar la carpeta:

```powershell
$env:MYSQL_BIN = "D:\mysql\bin"
```

## Cómo leer el resultado

| Estado | Significado |
| --- | --- |
| Aprobado | El sistema se comporta como se espera. |
| Defecto conocido | La prueba afirma el comportamiento deseado y hoy no se cumple. Tiene un código, como `REG-04`, y su detalle está en el informe. |
| Corregido | Un defecto conocido dejó de ocurrir: hay que quitar la marca `@defecto` de esa prueba. |
| Fallo | Algo que funcionaba dejó de funcionar, o la prueba tiene un error. |

La suite termina con error solo si hay un *Fallo* o un *Corregido*.

## Cómo agregar un caso

Cada prueba documenta su caso en el docstring, en una línea y con cuatro partes separadas por `|`:

```python
def test_jugador_de_otra_facultad(self):
    """CP-PLA-02 | Jugador de otra facultad | Inscribirlo en un equipo ajeno | Rechazo por facultad"""
    self.rechaza("INSERT INTO equipo_jugador_torneo VALUES (11,'66666661',2,50)", "facultad")
```

Para un defecto conocido, la prueba afirma lo deseado y lleva la marca con lo que pasa hoy:

```python
@defecto("REG-04", "Se aceptó: el plantel quedó con 3 docentes o funcionarios.")
def test_...(self):
```

Las clases base están en `tests/base.py`: `CasoTransaccional` para una conexión con rollback al final,
`CasoAislado` para reinstalar la base en cada prueba y `CasoWeb` para probar la aplicación.
