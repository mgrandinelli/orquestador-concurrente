# Ejercicio 1.1: Orquestador concurrente de modelos

Curso AI Engineering (Coderhouse), módulo 1, unidad "Arquitectura asíncrona con Python 3.12".

Simula un backend que consulta varios modelos de IA a la vez, con timeout y límite de concurrencia. No usa API keys: la latencia de red se simula con `asyncio.sleep`.

## Cómo ejecutarlo

Requiere Python 3.12 o superior. No tiene dependencias externas.

```bash
python3 main.py
```

Tarda unos 9,5 segundos.

## Qué hace

`main.py` tiene dos partes.

**Parte A: tres modelos en paralelo con timeout total.** Lanza `gpt_4_call` (1,0 s), `claude_3_call` (1,5 s) y `local_llama_call` (3,0 s) con `asyncio.gather`, dentro de un `asyncio.timeout` de 2 segundos. `local_llama_call` supera el límite a propósito: se captura el `TimeoutError`, se registra el error y el programa sigue. Las dos llamadas que terminaron a tiempo conservan su respuesta.

**Parte B: diez llamadas con `Semaphore(2)`.** Dispara 10 llamadas de golpe, pero el semáforo deja pasar solo 2 a la vez. Cada llamada tiene su propio timeout de 2 segundos, que empieza a contar cuando entra al semáforo y no mientras espera en la cola.

## Pasos del enunciado

| Paso | Dónde está en `main.py` |
|---|---|
| 1. Python 3.12+ | `asyncio.run(main())` como único punto de entrada |
| 2. Tres corrutinas con latencias distintas | `gpt_4_call`, `claude_3_call`, `local_llama_call` |
| 3. Orquestación con `asyncio.gather` | `orquestar()` |
| 4. `asyncio.timeout` de 2 s sobre la ejecución total | `orquestar()` |
| 5. `asyncio.Semaphore` con 10 llamadas y máximo 2 a la vez | `con_semaforo()` y `main()` |

## Criterios de aceptación

**No usa `time.sleep`.** Todas las esperas son `await asyncio.sleep()`.

**Las tareas inician casi al mismo tiempo.** Cada línea del log lleva los milisegundos desde el arranque; las tres llamadas empiezan en el mismo instante:

```
[   35ms] gpt_4_call       -> inicio
[   35ms] claude_3_call    -> inicio
[   35ms] local_llama_call -> inicio
```

**Maneja `TimeoutError`.** A los 2 segundos se cancela la llamada lenta y el programa continúa:

```
[ 1036ms] gpt_4_call       -> fin
[ 1536ms] claude_3_call    -> fin
[ 2036ms] TimeoutError: se superaron 2.0s; canceladas: ['local_llama_call']
[ 2036ms]   -> gpt_4_call: respuesta a '¿Qué es la entropía?'
[ 2036ms]   -> claude_3_call: respuesta a '¿Qué es la entropía?'
[ 2036ms]   -> sin respuesta (timeout)
[ 2036ms] El programa sigue tras el timeout
```

**El semáforo limita a 2 llamadas simultáneas.** En la parte B nunca hay más de dos llamadas entre su `inicio` y su `fin`. El resultado final es:

```
[ 9542ms] OK: 7/10 | fallidas: 3
```

Las 3 fallidas son las de `local_llama_call`, que siempre supera el timeout.
