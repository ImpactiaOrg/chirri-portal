# Images Pool — seed_demo

Imágenes que usa `python manage.py seed_demo` para thumbnails de TopContent
y la imagen del TextImageBlock intro.

## Estructura

```
images_pool/
├── post/      → feed / lifestyle / contenido (TopContent kind=POST + intro narrativo)
└── creator/   → retratos / perfiles (TopContent kind=CREATOR)
```

El seed pickea **aleatoriamente** de la subcarpeta correspondiente al
contexto. Las mismas imágenes se reusan. Si una subcarpeta está vacía, cae a
los placeholders en `../placeholder_*.jpg`.

## Formatos aceptados

`.jpg`, `.jpeg`, `.png`, `.webp`. Cualquier otro archivo (incluyendo este
README) es ignorado.

## Fuentes actuales

- `post/` — [Lorem Picsum](https://picsum.photos) con seeds reproducibles
  (`chirri-post-*`, `chirri-creator-*` — históricamente mixtos, ahora todos
  van a `post/`). Licencia Unsplash.
- `creator/` — [Pravatar](https://pravatar.cc) (avatars 1-70). "For
  development and prototypes only", que es nuestro caso de uso.

## Qué dropear

- **post/**: fotos tipo feed de Instagram — productos, ambientes, lifestyle.
- **creator/**: retratos/head shots — caras de gente (no mascotas, no logos).

Solo imágenes que tengas derecho a commitear al repo. Si no estás seguro,
no la subas.
