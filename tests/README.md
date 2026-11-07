# Tests del proyecto

Pruebas con `unittest` para validar los scripts SQL (restricciones, triggers y procedimientos), los permisos por rol en MySQL, la aplicación Flask y los reportes.

## Ejecución

Desde la raíz del proyecto, con el entorno virtual activo (`pymysql` y `flask` instalados):

```powershell
python tests/run_tests.py
```

Para correr un archivo en particular se puede pasar parte del nombre:

```powershell
python tests/run_tests.py sancion
python tests/run_tests.py roles
```

## Base de datos temporal

Al iniciar las pruebas, `tests/base.py` levanta una instancia temporal de `mysqld` en un puerto libre con una carpeta de datos temporal, ejecuta los cuatro scripts de `Scripts/` y la apaga al terminar. De esta forma no modifica ni borra una base `torneo_futbol5` que tengas cargada localmente.

Solo requiere tener MySQL Server 8 instalado en el equipo. Si los binarios no están en `C:\Program Files\MySQL\MySQL Server 8.x\bin`, se puede indicar la ruta antes de correr los tests:

```powershell
$env:MYSQL_BIN = "D:\mysql\bin"
```
