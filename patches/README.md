# Parche: sincronización de gag-viewer-poc

`gag-viewer-poc-sync.patch` contiene el commit que actualiza el motor AlmaGag
embebido en https://github.com/Josexato/gag-viewer-poc a la versión actual de
este repositorio (post-PR #31).

Está guardado aquí porque la app de GitHub de Claude no tiene acceso de
escritura al repo `gag-viewer-poc`. Para aplicarlo:

```bash
cd gag-viewer-poc
git checkout -b claude/gag-viewer-poc-update-zof2vc
git am ruta/al/gag-viewer-poc-sync.patch
git push -u origin claude/gag-viewer-poc-update-zof2vc
```

Una vez concedido el acceso (GitHub → Settings → Installations → Claude →
Repository access → añadir `gag-viewer-poc`), este parche puede eliminarse y
Claude podrá subir la rama directamente.
