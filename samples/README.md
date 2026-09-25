# Muestras locales

Los audios de prueba no se versionan. Para armar uno a partir de un archivo que ya tengas:

```powershell
python scripts\preparar-muestra.py D:\charla.mp4 --nombre sesion-1
```

Eso usa ffmpeg y deja `samples/sesion-1.wav` en mono, 16 kHz. En la interfaz, elegí la sesión y cargá ese archivo. Repetí con otro nombre para la segunda sesión.

Hace falta ffmpeg en el PATH. En Windows lo instala `scripts/setup-windows.ps1`.
