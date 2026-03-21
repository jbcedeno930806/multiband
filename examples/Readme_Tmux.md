## **Tmux Basico**

Para correr multiples scripts, ver su salida y cerrar la terminal sin detenerlos.

1. Iniciar sesion

```bash
tmux new -s sims
```

2. Dividir pantalla
   Presiona Ctrl + b y luego " (horizontal) o % (vertical).

3. Moverse entre paneles
   Presiona Ctrl + b y usa las flechas del teclado.

4. Ejecutar scripts
   Lanza `python3 script1.py` en un panel y `python3 script2.py` en el otro.

5. Salir sin cerrar (Detach)
   Presiona Ctrl + b y luego d. Ya puedes cerrar tu SSH.
   Recuperar sesion:

```bash
tmux attach -t sims
```

**Cerrar Sesion**

1. Cerrar la sesion actual

```bash
tmux kill-session -t session-name
```

2. Cerrar una sesion especifica

```bash
tmux kill-session -t session-name
```

3. Cerrar todas

```bash
tmux kill-session
```

o alternativamente:

```bash
tmux -S tmux -S /var/tmux-shared/sesion1 kill-session
```

## **Compartir Sesion (Opcional)**

Grupo dedicado + carpeta con herencia de permisos (SGID + ACL).

1. Crear el grupo y la carpeta

```bash
sudo addgroup tmux-shared
sudo mkdir /var/tmux-shared
sudo chgrp tmux-shared /var/tmux-shared
```

2. Agregar usuarios al grupo

```bash
sudo usermod -aG tmux-shared usuario1
sudo usermod -aG tmux-shared usuario2
```

3. Configurar herencia de permisos (SGID y ACL)
   Bit SGID: obliga a que todo lo que se cree dentro pertenezca al grupo `tmux-shared`.

```bash
sudo chmod g+ws /var/tmux-shared
```

ACL por defecto: asegura que los nuevos archivos tengan permisos de lectura y escritura para el grupo.

```bash
sudo setfacl -d -m g:tmux-shared:rw /var/tmux-shared
```

4. Iniciar la sesion compartida (Usuario A)

```bash
tmux -S /var/tmux-shared/sesion1 new -s compartida
```

5. Unirse a la sesion en modo solo lectura (Usuario B)

```bash
tmux -S /var/tmux-shared/sesion1 attach -r
```

**Nota: Si otros usuarios no pueden entrar (permisos)**
Revisa estos puntos:

1. El usuario debe refrescar el grupo (cerrar sesion y volver a entrar) o ejecutar:

```bash
newgrp tmux-shared
```

2. La carpeta debe permitir escritura y ejecucion para el grupo:

```bash
sudo chgrp tmux-shared /var/tmux-shared
sudo chmod 2775 /var/tmux-shared
sudo setfacl -m g:tmux-shared:rwx /var/tmux-shared
sudo setfacl -d -m g:tmux-shared:rwx /var/tmux-shared
```

3. Si el socket ya existia con permisos malos, borrarlo y crear la sesion de nuevo:

```bash
sudo rm /var/tmux-shared/sesion1
tmux -S /var/tmux-shared/sesion1 new -s compartida
```

Si necesitas otorgar permisos de escritura a otras personas en un socket existente:

```bash
chmod g+rw /var/tmux-shared/nombre_sesion
```

Verifica permisos del socket:

```bash
ls -l /var/tmux-shared/sesion1
```

**Nota: Control de acceso en tmux (server-access)**
Algunas versiones de tmux requieren habilitar acceso adicional por usuario.
Ejecuta estos comandos usando el mismo socket:

```bash
tmux -S /var/tmux-shared/sesion1 server-access -a usuario2
```

Para listar usuarios permitidos:

```bash
tmux -S /var/tmux-shared/sesion1 server-access -l
```

Si tu version de tmux no soporta `server-access`, el comando fallara.

6. Cerrar la sesion:

```bash
tmux -S /var/tmux-shared/sesion1 kill-session
```
