"""azd predeploy hook: build + push the relay image, point the Container App at it. OWNER: A (potencialbg).

azure.yaml runs this before every `azd up` / `azd deploy` (D17: no ACR Tasks on the free subscription, no Docker here).
It also saves the image as RELAY_IMAGE in the azd env, so a later `azd provision` keeps it (infra/main.parameters.json).
Needs az login and `pip install uv`. Prints names and the image tag only, never a token.
"""
from __future__ import annotations

import os
import sys

from .push_image import build_and_push, registry_from_env, sh


def env(name: str) -> str:
    return (os.environ.get(name) or sh("azd", "env", "get-value", name)).strip().strip('"')


def main() -> int:
    image = build_and_push(registry_from_env())
    app, rg = env("RELAY_APP_NAME"), env("AZURE_RESOURCE_GROUP")
    current = sh("az", "containerapp", "show", "-n", app, "-g", rg, "--query",
                 "properties.template.containers[0].image", "-o", "tsv").strip()
    if current != image:
        sh("az", "containerapp", "update", "-n", app, "-g", rg, "--image", image, "-o", "none")
    sh("azd", "env", "set", "RELAY_IMAGE", image)
    print(f"relay: {image} ({'unchanged' if current == image else 'deployed'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
