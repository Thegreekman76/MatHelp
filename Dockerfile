# MatHelp — imagen de producción (binario nativo).
#
# Tres etapas:
#   vendor  — clona fitz-liveviews. Existe porque la imagen oficial de Fitz
#             NO trae `git`, así que no puede resolver una dependencia
#             { git = ... } adentro del container. Clonamos acá y adentro la
#             usamos como { path = ... } (fitz.docker.toml).
#   builder — imagen oficial de Fitz (trae el toolchain): `fitz build` compila
#             a binario nativo estático.
#   runtime — distroless/cc: solo glibc + libgcc. Sin Fitz, sin Rust, sin shell.
#
# ─────────────────────────────────────────────────────────────────────────
# BINARIO NATIVO
#
# Desde fitz v0.55.0 el codegen compila todo lo que MatHelp usa (cookies
# nativas, Response.cookies, y liveviews v0.50). Antes esto no se podía: el
# codegen de fitz v0.47 rompía funciones `Str?` con `return null` (FITZ-09) y
# no importaba helpers de cookies cross-module (FITZ-05 cross-module) — dos
# bugs que el dogfooding de MatHelp encontró y que ya están cerrados. Resultado:
# binario estático, ~9x más rápido que el intérprete, imagen distroless mínima.
# ─────────────────────────────────────────────────────────────────────────

ARG FITZ_IMAGE=ghcr.io/thegreekman76/fitz:v0.57.0
ARG FLV_TAG=v0.50.0

# ---- Stage 1: vendor ----------------------------------------------------
FROM alpine:3.20 AS vendor

ARG FLV_TAG
RUN apk add --no-cache git
RUN git clone --depth 1 --branch ${FLV_TAG} \
      https://github.com/Thegreekman76/fitz-liveviews.git \
      /vendor/fitz-liveviews \
 && rm -rf /vendor/fitz-liveviews/.git

# ---- Stage 2: builder ---------------------------------------------------
FROM ${FITZ_IMAGE} AS builder

WORKDIR /app

COPY --from=vendor /vendor/fitz-liveviews /vendor/fitz-liveviews

# fitz.docker.toml es idéntico a fitz.toml salvo que apunta la dependencia al
# vendor local. Así no hace falta ni git ni red adentro del container.
COPY fitz.docker.toml ./fitz.toml
COPY src/ ./src/
COPY public/ ./public/

# Compila a binario nativo. El resultado queda en target/release/mathelp.
RUN fitz build

# ---- Stage 3: runtime ---------------------------------------------------
FROM gcr.io/distroless/cc-debian12

WORKDIR /app

COPY --from=builder /app/target/release/mathelp /usr/local/bin/mathelp
# public/ se lee del disco en runtime (static_dir). Copiamos los estáticos.
COPY --from=builder /app/public /app/public

# @server(3000, "0.0.0.0") — el "0.0.0.0" es obligatorio: sin eso el -p del
# host no rutea nada hacia adentro del contenedor.
EXPOSE 3000

ENTRYPOINT ["/usr/local/bin/mathelp"]
