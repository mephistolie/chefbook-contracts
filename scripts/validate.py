#!/usr/bin/env python3
"""Validate the public contract using a checksum-pinned OpenAPI Generator."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import yaml
from request_examples import validate_request_examples

ROOT = Path(__file__).resolve().parents[1]
VERSION = "7.14.0"
SHA256 = "e03186835022ca02da4aa95e3967b6a3b6d44c2e5f7606e6d5c22466f519c757"
URL = (
    "https://repo.maven.apache.org/maven2/org/openapitools/openapi-generator-cli/"
    f"{VERSION}/openapi-generator-cli-{VERSION}.jar"
)


def verified(path):
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == SHA256


def main():
    subprocess.run([sys.executable, str(ROOT / "scripts/bundle.py"), "--check"], check=True)
    examples = validate_request_examples(yaml.safe_load((ROOT / "openapi/chefbook.yaml").read_text()))
    print(f'Validated {examples} named JSON request examples', flush=True)
    override = os.environ.get("OPENAPI_GENERATOR_JAR")
    jar = Path(override) if override else ROOT / ".cache" / f"openapi-generator-{VERSION}.jar"
    if override and not verified(jar):
        raise SystemExit("OPENAPI_GENERATOR_JAR must point to the checksum-pinned 7.14.0 jar")
    if not verified(jar):
        jar.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=jar.parent, delete=False) as stream:
            download = Path(stream.name)
        try:
            with urllib.request.urlopen(URL, timeout=60) as response, download.open("wb") as stream:
                while chunk := response.read(1024 * 1024):
                    stream.write(chunk)
            if not verified(download):
                raise SystemExit("OpenAPI Generator download checksum mismatch")
            download.replace(jar)
        finally:
            download.unlink(missing_ok=True)
    # The source is a bundler manifest with x-path-sources, not a standalone spec.
    # bundle.py --check above resolves and checks the sources before validation.
    subprocess.run(
        ["java", "-jar", str(jar), "validate", "-i", str(ROOT / "openapi/chefbook.yaml")],
        check=True,
    )


if __name__ == "__main__":
    main()
