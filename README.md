# Monitor Austria Working Holiday — Buenos Aires

**Estado:** código inicial, **no probado contra el formulario en vivo**. No hace reservas.

## Instalación
1. Crear un repositorio **público** nuevo en GitHub. No incluir datos personales en el repositorio.
2. Subir `monitor.py`, `requirements.txt` y `.github/workflows/monitor.yml` conservando las rutas.
3. En iPhone, abrir ntfy y suscribirse a un tema impredecible y largo (por ejemplo, 32 caracteres aleatorios). Nunca publicar el tema.
4. GitHub > repositorio > Settings > Secrets and variables > Actions > New repository secret. Nombre `NTFY_TOPIC`, valor: **solo** el nombre del tema de ntfy, sin URL.
5. GitHub > Actions > Austria WHV appointment monitor > Run workflow para probar. Revisar los logs. La prueba inicial puede fallar si los controles reales no son selects HTML; en ese caso consultar `diagnostics` en el workflow fallido.
6. Si la prueba funciona, GitHub ejecuta el cron cada ~5 minutos (puede demorarse, o suspenderse por inactividad según reglas de GitHub).

## Limitaciones importantes
- Solo inspecciona la semana que presenta el sitio al avanzar; **no revisa otras semanas**.
- Solo alerta ante horarios visibles con formato HH:MM en enlaces o botones. Otros formatos de disponibilidad pueden no detectarse.
- No informa falsamente que hay turnos si cambia el texto: guarda diagnóstico para revisión.
- El tema ntfy es una dirección compartible; usar un nombre aleatorio largo y mantenerlo en secreto.
- No intenta eludir CAPTCHA ni bloqueos, ni confirma una reserva.
- GitHub Actions no garantiza precisión de 5 minutos y puede deshabilitar cron por inactividad en repositorios públicos.
- La Embajada no vende turnos. No pagar a terceros.
