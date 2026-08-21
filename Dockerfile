# MatHelp — imagen de producción.
#
# Dos etapas:
#   vendor  — clona fitz-liveviews. Existe porque la imagen oficial de Fitz
#             NO trae `git`, así que `fitz build` / `fitz run` no pueden
#             resolver una dependencia { git = ... } adentro del container.
#             Clonamos acá y adentro la usamos como { path = ... }.
#   runtime — imagen oficial de Fitz, corriendo el intérprete.
#
# ─────────────────────────────────────────────────────────────────────────
# POR QUÉ INTERPRETADO Y NO BINARIO NATIVO
#
# Lo ideal sería `fitz build` + runtime distroless: binario estático, ~9x más
# rápido, imagen mínima. Hoy no se puede: el codegen de Fitz v0.47.0 rompe al
# compilar funciones que devuelven `Str?` y hacen `return null` adentro —
# emite `return ()` en vez de `return None`. `fitz check` y `fitz run` lo
# aceptan sin chistar; `fitz build` falla con E0308.
#
# Y no alcanza con evitarlo en nuestro código: `flv_cookie`, DENTRO de
# fitz-liveviews, tiene el mismo patrón. Cualquier proyecto que dependa de la
# librería y compile a nativo choca con esto.
#
# Repro de 20 líneas y detalle en docs/BUG-fitz-option-codegen.md.
#
# Para un juego de matemática en la red de casa, el intérprete sobra. Cuando
# el bug esté arreglado, se cambia a la versión compilada: está más abajo,
# comentada, lista para descomentar.
# ─────────────────────────────────────────────────────────────────────────

ARG FITZ_IMAGE=ghcr.io/thegreekman76/fitz:latest
ARG FLV_TAG=v0.47.0

# ---- Stage 1: vendor ----------------------------------------------------
FROM alpine:3.20 AS vendor

ARG FLV_TAG
RUN apk add --no-cache git
RUN git clone --depth 1 --branch ${FLV_TAG} \
      https://github.com/Thegreekman76/fitz-liveviews.git \
      /vendor/fitz-liveviews \
 && rm -rf /vendor/fitz-liveviews/.git

# ---- Stage 2: runtime ---------------------------------------------------
FROM ${FITZ_IMAGE}

WORKDIR /app

COPY --from=vendor /vendor/fitz-liveviews /vendor/fitz-liveviews

# fitz.docker.toml es idéntico a fitz.toml salvo que apunta la dependencia al
# vendor local. Así no hace falta ni git ni red adentro del container.
COPY fitz.docker.toml ./fitz.toml
COPY src/ ./src/

# Resuelve dependencias y escribe el lock ahora, no en el primer request.
RUN fitz check

# @server(3000, "0.0.0.0") — el "0.0.0.0" es obligatorio: sin eso el -p del
# host no rutea nada hacia adentro del contenedor.
EXPOSE 3000

CMD ["fitz", "run"]

# ─── Versión compilada — descomentar cuando se arregle el codegen ─────────
#
# FROM ${FITZ_IMAGE} AS builder
# WORKDIR /app
# COPY --from=vendor /vendor/fitz-liveviews /vendor/fitz-liveviews
# COPY fitz.docker.toml ./fitz.toml
# COPY src/ ./src/
# RUN fitz build
#
# FROM gcr.io/distroless/cc-debian12
# COPY --from=builder /app/target/release/mathelp /usr/local/bin/mathelp
# EXPOSE 3000
# ENTRYPOINT ["/usr/local/bin/mathelp"]
