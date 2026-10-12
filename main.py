"""Ejercicio 1.1 - Orquestador concurrente de modelos (Python 3.12+)."""

import asyncio
import logging
from itertools import cycle

logging.basicConfig(level=logging.INFO, format="[%(relativeCreated)5.0fms] %(message)s")
log = logging.getLogger(__name__)

TIMEOUT_S = 2.0


# --- 2. Simulación de llamadas (latencias distintas, nunca time.sleep) ---
async def _simular(nombre: str, latencia: float, prompt: str) -> str:
    log.info("%-16s -> inicio", nombre)
    await asyncio.sleep(latencia)
    log.info("%-16s -> fin", nombre)
    return f"{nombre}: respuesta a '{prompt}'"


async def gpt_4_call(prompt: str) -> str:
    return await _simular("gpt_4_call", 1.0, prompt)


async def claude_3_call(prompt: str) -> str:
    return await _simular("claude_3_call", 1.5, prompt)


async def local_llama_call(prompt: str) -> str:
    return await _simular("local_llama_call", 3.0, prompt)  # supera el timeout a propósito


MODELOS = [gpt_4_call, claude_3_call, local_llama_call]


# --- 3 y 4. Orquestación con timeout sobre la ejecución total ---
async def orquestar(prompt: str) -> list[str | None]:
    """Lanza todos los modelos a la vez; devuelve None para los que no llegaron a tiempo."""
    tareas = [asyncio.create_task(m(prompt), name=m.__name__) for m in MODELOS]
    try:
        async with asyncio.timeout(TIMEOUT_S):
            await asyncio.gather(*tareas)
    except TimeoutError:
        canceladas = [t.get_name() for t in tareas if not t.done() or t.cancelled()]
        log.error("TimeoutError: se superaron %.1fs; canceladas: %s", TIMEOUT_S, canceladas)

    # Las tareas que terminaron antes del timeout conservan su resultado.
    resultados = await asyncio.gather(*tareas, return_exceptions=True)
    return [None if isinstance(r, BaseException) else r for r in resultados]


# --- 5. Control de flujo: semáforo, con timeout por llamada ---
async def con_semaforo(sem: asyncio.Semaphore, modelo, prompt: str) -> str | None:
    async with sem:
        try:
            # Dentro del semáforo: el tiempo en cola no cuenta para el timeout.
            async with asyncio.timeout(TIMEOUT_S):
                return await modelo(prompt)
        except TimeoutError:
            log.error("TimeoutError: %s superó %.1fs (%s)", modelo.__name__, TIMEOUT_S, prompt)
            return None


async def main() -> None:
    log.info("=== Parte A: 3 modelos en paralelo con gather, timeout total ===")
    for r in await orquestar("¿Qué es la entropía?"):
        log.info("  -> %s", r or "sin respuesta (timeout)")
    log.info("El programa sigue tras el timeout")

    log.info("=== Parte B: 10 llamadas, Semaphore(2) ===")
    sem = asyncio.Semaphore(2)
    modelos = cycle(MODELOS)
    # return_exceptions=True: un fallo inesperado vuelve como resultado, no tumba el lote.
    resultados = await asyncio.gather(
        *(con_semaforo(sem, next(modelos), f"pregunta {i}") for i in range(10)),
        return_exceptions=True,
    )
    ok = sum(isinstance(r, str) for r in resultados)
    log.info("OK: %d/10 | fallidas: %d", ok, 10 - ok)


if __name__ == "__main__":
    asyncio.run(main())
