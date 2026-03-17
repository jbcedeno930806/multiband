## 🚀 Ejecución Persistente con Tmux

### Para correr múltiples scripts, ver su salida y cerrar la terminal sin detenerlos:

### 1. Iniciar sesión

```bash
tmux new -s mis_scripts
```

### 2. Dividir pantalla:

Presiona Ctrl + b y luego " (horizontal) o % (vertical).

### 3. Moverse entre paneles:

Presiona Ctrl + b y usa las flechas del teclado.

### 4. Ejecutar scripts:

Lanza python3 script1.py en un panel y python3 script2.py en el otro.

### 5. Salir sin cerrar (Detach):

Presiona Ctrl + b y luego d. Ya puedes cerrar tu SSH.
Recuperar sesión:
tmux attach -t mis_scripts
