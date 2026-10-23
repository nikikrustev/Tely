"""Stage 5 evaluation: spoiler leaks, numbers, Director calls and fallbacks, real-time latency. OWNER: A (potencialbg).

    python -m audiostands.eval --cut judge                 # (a) + (c) locally, writes eval/report.json
    python -m audiostands.eval --cut judge --foundry-eval  # (c) also uploaded and run as a Foundry custom evaluator
    python -m audiostands.eval --cut judge --realtime      # (b) live Director + TTS at wall-clock speed (Azure)
Then: python eval/build_report.py  (merges B's eval/qa.json and eval/listening.json into eval/report.md)
"""
